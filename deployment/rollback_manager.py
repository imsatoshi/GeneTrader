"""
Automatic rollback manager for strategy deployments.

This module monitors deployed strategies and automatically rolls back
to previous versions when performance degrades beyond thresholds.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from utils.logging_config import logger

from deployment.version_control import StrategyVersionControl, VersionStatus
from monitoring.performance_monitor import PerformanceMonitor, PerformanceMetrics
from monitoring.degradation_detector import DegradationDetector, DetectionResult, AlertSeverity


class RollbackReason(Enum):
    """Reasons for triggering a rollback."""
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    PROFIT_DECLINE = "profit_decline"
    WIN_RATE_DROP = "win_rate_drop"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    CRITICAL_ALERT = "critical_alert"
    MANUAL = "manual"
    HEALTH_CHECK_FAILED = "health_check_failed"


@dataclass
class RollbackEvent:
    """Record of a rollback event."""
    timestamp: datetime
    strategy_name: str
    from_version: str
    to_version: str
    reason: RollbackReason
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    success: bool
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'strategy_name': self.strategy_name,
            'from_version': self.from_version,
            'to_version': self.to_version,
            'reason': self.reason.value,
            'metrics_before': self.metrics_before,
            'metrics_after': self.metrics_after,
            'success': self.success,
            'notes': self.notes,
        }


@dataclass
class RollbackConfig:
    """Configuration for automatic rollback."""
    enabled: bool = False
    max_drawdown: float = 0.15
    max_consecutive_losses: int = 5
    min_win_rate: float = 0.30
    profit_decline_threshold: float = 0.50  # 50% decline from baseline
    check_interval_minutes: int = 5
    cooldown_minutes: int = 60  # Minimum time between rollbacks
    notify_on_rollback: bool = True
    require_confirmation: bool = True


class RollbackManager:
    """
    Manages automatic rollback of strategy deployments.

    Monitors live performance and automatically rolls back to previous
    versions when degradation is detected.

    Features:
    - Configurable thresholds for rollback triggers
    - Cooldown period between rollbacks
    - Rollback history tracking
    - Optional confirmation before rollback
    - Notification callbacks
    """

    def __init__(
        self,
        version_control: StrategyVersionControl,
        performance_monitor: Optional[PerformanceMonitor] = None,
        degradation_detector: Optional[DegradationDetector] = None,
        config: Optional[RollbackConfig] = None,
        rollback_history_file: str = "data/rollback_history.json"
    ):
        """
        Initialize rollback manager.

        Args:
            version_control: Version control system
            performance_monitor: Performance monitoring system
            degradation_detector: Degradation detection system
            config: Rollback configuration
            rollback_history_file: Path to store rollback history
        """
        self.version_control = version_control
        self.monitor = performance_monitor
        self.detector = degradation_detector
        self.config = config or RollbackConfig()
        self.history_file = rollback_history_file

        self._history: List[RollbackEvent] = []
        self._last_rollback_time: Dict[str, datetime] = {}
        self._notify_callback: Optional[Callable[[RollbackEvent], None]] = None
        self._confirm_callback: Optional[Callable[[str, str, RollbackReason], bool]] = None
        self._deploy_callback: Optional[Callable[[str, str], bool]] = None

        self._load_history()

    def _load_history(self) -> None:
        """Load rollback history from file."""
        if not os.path.exists(self.history_file):
            return

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)

            self._history = []
            for event_data in data.get('events', []):
                self._history.append(RollbackEvent(
                    timestamp=parse_utc(event_data['timestamp']),
                    strategy_name=event_data['strategy_name'],
                    from_version=event_data['from_version'],
                    to_version=event_data['to_version'],
                    reason=RollbackReason(event_data['reason']),
                    metrics_before=event_data.get('metrics_before', {}),
                    metrics_after=event_data.get('metrics_after', {}),
                    success=event_data.get('success', True),
                    notes=event_data.get('notes', ''),
                ))

        except Exception as e:
            logger.error(f"Error loading rollback history: {e}")

    def _save_history(self) -> None:
        """Save rollback history to file."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        data = {
            'events': [e.to_dict() for e in self._history]
        }

        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_notify_callback(self, callback: Callable[[RollbackEvent], None]) -> None:
        """Set callback for rollback notifications."""
        self._notify_callback = callback

    def set_confirm_callback(
        self,
        callback: Callable[[str, str, RollbackReason], bool]
    ) -> None:
        """
        Set callback for rollback confirmation.

        Args:
            callback: Function(strategy_name, version_id, reason) -> bool
        """
        self._confirm_callback = callback

    def set_deploy_callback(self, callback: Callable[[str, str], bool]) -> None:
        """
        Set callback for deploying a version.

        Args:
            callback: Function(strategy_name, version_id) -> bool
        """
        self._deploy_callback = callback

    def check_and_rollback(
        self,
        strategy_name: str,
        metrics: Optional[PerformanceMetrics] = None
    ) -> Optional[RollbackEvent]:
        """
        Check if rollback is needed and execute if so.

        Args:
            strategy_name: Strategy to check
            metrics: Current performance metrics (fetched if not provided)

        Returns:
            RollbackEvent if rollback occurred, None otherwise
        """
        if not self.config.enabled:
            return None

        # Check cooldown
        last_rollback = self._last_rollback_time.get(strategy_name)
        if last_rollback:
            elapsed = (utc_now() - last_rollback).total_seconds() / 60
            if elapsed < self.config.cooldown_minutes:
                logger.debug(f"Rollback cooldown active for {strategy_name}")
                return None

        # Get current metrics
        if metrics is None and self.monitor:
            metrics = self.monitor.get_current_metrics()

        if metrics is None:
            return None

        # Check triggers
        reason = self._check_triggers(metrics)

        if reason is None:
            return None

        logger.warning(f"Rollback triggered for {strategy_name}: {reason.value}")

        # Execute rollback
        return self.execute_rollback(strategy_name, reason, metrics)

    def _check_triggers(self, metrics: PerformanceMetrics) -> Optional[RollbackReason]:
        """
        Check if any rollback triggers are met.

        Args:
            metrics: Current performance metrics

        Returns:
            RollbackReason if triggered, None otherwise
        """
        # Check drawdown
        if metrics.max_drawdown > self.config.max_drawdown:
            return RollbackReason.DRAWDOWN_EXCEEDED

        # Check consecutive losses
        if metrics.max_consecutive_losses >= self.config.max_consecutive_losses:
            return RollbackReason.CONSECUTIVE_LOSSES

        # Check win rate
        if metrics.total_trades >= 10 and metrics.win_rate < self.config.min_win_rate:
            return RollbackReason.WIN_RATE_DROP

        return None

    def check_with_detector(
        self,
        strategy_name: str,
        detection_result: DetectionResult
    ) -> Optional[RollbackEvent]:
        """
        Check for rollback based on degradation detector results.

        Args:
            strategy_name: Strategy name
            detection_result: Result from degradation detector

        Returns:
            RollbackEvent if rollback occurred
        """
        if not self.config.enabled:
            return None

        # Check for critical alerts
        critical_alerts = [
            a for a in detection_result.alerts
            if a.severity == AlertSeverity.CRITICAL
        ]

        if not critical_alerts:
            return None

        # Determine reason from alert type
        reason = RollbackReason.CRITICAL_ALERT

        return self.execute_rollback(
            strategy_name,
            reason,
            detection_result.live_metrics if hasattr(detection_result, 'live_metrics') else None
        )

    def execute_rollback(
        self,
        strategy_name: str,
        reason: RollbackReason,
        metrics_before: Optional[Any] = None
    ) -> Optional[RollbackEvent]:
        """
        Execute a rollback to previous version.

        Args:
            strategy_name: Strategy to rollback
            reason: Reason for rollback
            metrics_before: Metrics before rollback

        Returns:
            RollbackEvent if successful
        """
        # Get current and previous versions
        current = self.version_control.get_active_version(strategy_name)
        if not current:
            logger.error(f"No active version found for {strategy_name}")
            return None

        # Find previous version
        history = self.version_control.get_deployment_history(strategy_name)
        previous_version = None

        for h in history:
            if h['version_id'] != current.version_id:
                previous_version = h['version_id']
                break

        if not previous_version:
            logger.error(f"No previous version to rollback to for {strategy_name}")
            return None

        metrics_before_dict = metrics_before.__dict__ if hasattr(metrics_before, '__dict__') else {}

        # Confirmation check
        if self.config.require_confirmation:
            if not self._confirm_callback:
                logger.error(f"Rollback confirmation callback required for {strategy_name}")
                return None
            if not self._confirm_callback(strategy_name, previous_version, reason):
                logger.info(f"Rollback not confirmed for {strategy_name}")
                return None

        # Execute rollback. Without a deploy callback the strategy file would
        # never be restored, so record the failure instead of faking success.
        if not self._deploy_callback:
            logger.error(f"Rollback deploy callback required for {strategy_name}")
            event = RollbackEvent(
                timestamp=utc_now(),
                strategy_name=strategy_name,
                from_version=current.version_id,
                to_version=previous_version,
                reason=reason,
                metrics_before=metrics_before_dict,
                metrics_after={},
                success=False,
                notes="deploy_callback_required",
            )
            self._history.append(event)
            self._save_history()
            return event

        success = self._deploy_callback(strategy_name, previous_version)
        if success:
            self.version_control.update_status(
                strategy_name, current.version_id, VersionStatus.ROLLED_BACK
            )
            self.version_control.set_active(strategy_name, previous_version)

        # Create event
        event = RollbackEvent(
            timestamp=utc_now(),
            strategy_name=strategy_name,
            from_version=current.version_id,
            to_version=previous_version,
            reason=reason,
            metrics_before=metrics_before_dict,
            metrics_after={},
            success=success,
        )

        # Record rollback
        self._history.append(event)
        self._last_rollback_time[strategy_name] = utc_now()
        self._save_history()

        # Notify
        if self._notify_callback:
            self._notify_callback(event)

        logger.info(f"Rollback {'successful' if success else 'failed'}: "
                   f"{strategy_name} {current.version_id} -> {previous_version}")

        return event

    def manual_rollback(
        self,
        strategy_name: str,
        to_version: Optional[str] = None,
        notes: str = ""
    ) -> Optional[RollbackEvent]:
        """
        Perform a manual rollback.

        Args:
            strategy_name: Strategy to rollback
            to_version: Target version (previous if not specified)
            notes: Notes for the rollback

        Returns:
            RollbackEvent if successful
        """
        current = self.version_control.get_active_version(strategy_name)
        if not current:
            return None

        if not to_version:
            history = self.version_control.get_deployment_history(strategy_name)
            for h in history:
                if h['version_id'] != current.version_id:
                    to_version = h['version_id']
                    break

        if not to_version:
            logger.error("No target version for rollback")
            return None

        event = self.execute_rollback(strategy_name, RollbackReason.MANUAL, None)

        if event:
            event.notes = notes

        return event

    def get_history(
        self,
        strategy_name: Optional[str] = None,
        limit: int = 50
    ) -> List[RollbackEvent]:
        """
        Get rollback history.

        Args:
            strategy_name: Filter by strategy name
            limit: Maximum number of events

        Returns:
            List of RollbackEvent objects
        """
        events = self._history

        if strategy_name:
            events = [e for e in events if e.strategy_name == strategy_name]

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:limit]

    def get_rollback_count(
        self,
        strategy_name: str,
        hours: int = 24
    ) -> int:
        """
        Get number of rollbacks in a time period.

        Args:
            strategy_name: Strategy name
            hours: Time period in hours

        Returns:
            Number of rollbacks
        """
        cutoff = utc_now() - timedelta(hours=hours)

        return sum(
            1 for e in self._history
            if e.strategy_name == strategy_name and e.timestamp >= cutoff
        )

    def is_in_cooldown(self, strategy_name: str) -> bool:
        """Check if strategy is in rollback cooldown."""
        last_rollback = self._last_rollback_time.get(strategy_name)
        if not last_rollback:
            return False

        elapsed = (utc_now() - last_rollback).total_seconds() / 60
        return elapsed < self.config.cooldown_minutes

    def get_cooldown_remaining(self, strategy_name: str) -> int:
        """
        Get remaining cooldown time in minutes.

        Args:
            strategy_name: Strategy name

        Returns:
            Minutes remaining in cooldown, 0 if not in cooldown
        """
        last_rollback = self._last_rollback_time.get(strategy_name)
        if not last_rollback:
            return 0

        elapsed = (utc_now() - last_rollback).total_seconds() / 60
        remaining = self.config.cooldown_minutes - elapsed

        return max(0, int(remaining))

    def clear_history(self, strategy_name: Optional[str] = None) -> int:
        """
        Clear rollback history.

        Args:
            strategy_name: Clear only for this strategy

        Returns:
            Number of events cleared
        """
        if strategy_name:
            original_count = len(self._history)
            self._history = [
                e for e in self._history
                if e.strategy_name != strategy_name
            ]
            cleared = original_count - len(self._history)
        else:
            cleared = len(self._history)
            self._history = []

        self._save_history()
        return cleared

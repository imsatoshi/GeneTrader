"""
Adaptive optimizer - main orchestrator for on-the-fly optimization.

This module provides the core adaptive optimization system that monitors
live trading, detects degradation, and triggers re-optimization automatically.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from utils.logging_config import logger

from monitoring.freqtrade_client import FreqtradeClient
from monitoring.performance_monitor import PerformanceMonitor
from monitoring.performance_db import PerformanceDB
from monitoring.degradation_detector import DegradationDetector, DetectionResult
from deployment.version_control import StrategyVersionControl
from deployment.strategy_deployer import StrategyDeployer, DeploymentConfig
from deployment.shadow_trader import ShadowTrader, ShadowConfig
from deployment.rollback_manager import RollbackManager, RollbackConfig


class AdaptiveState(Enum):
    """State of the adaptive optimization system."""
    IDLE = "idle"
    MONITORING = "monitoring"
    DEGRADATION_DETECTED = "degradation_detected"
    OPTIMIZING = "optimizing"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    COOLDOWN = "cooldown"
    ERROR = "error"


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive optimization."""
    # Monitoring settings
    check_interval_minutes: int = 5
    metrics_window_hours: int = 168  # 7 days

    # Degradation detection
    degradation_threshold: float = 0.3
    min_trades_for_evaluation: int = 20

    # Optimization triggers
    profit_decline_trigger: float = 0.5  # 50% decline from baseline
    drawdown_trigger: float = 0.20
    win_rate_decline_trigger: float = 0.15

    # Optimization settings
    optimization_days: int = 90
    recent_data_weight: float = 0.7
    population_size: int = 50
    generations: int = 30

    # Deployment settings
    shadow_trading_hours: int = 24
    gradual_rollout: bool = True
    auto_rollback_enabled: bool = True

    # Rate limiting
    min_hours_between_optimizations: int = 72  # 3 days
    max_optimizations_per_week: int = 2

    # Approval settings
    require_approval: bool = True
    auto_approve_threshold: float = 0.8  # Reserved for future explicit approval policy


@dataclass
class OptimizationEvent:
    """Record of an optimization event."""
    timestamp: datetime
    strategy_name: str
    trigger_reason: str
    old_version: str
    new_version: str
    success: bool
    improvement_pct: float
    notes: str = ""


class AdaptiveOptimizer:
    """
    Main orchestrator for adaptive strategy optimization.

    Workflow:
    1. Monitor: Continuously monitor live trading performance
    2. Detect: Detect strategy degradation using statistical methods
    3. Decide: Determine if re-optimization is needed
    4. Optimize: Run weighted optimization favoring recent data
    5. Validate: Validate new strategy with shadow trading
    6. Deploy: Deploy with gradual rollout
    7. Monitor: Return to monitoring

    Usage:
        adaptive = AdaptiveOptimizer(
            strategy_name="MyStrategy",
            freqtrade_client=client,
            config=AdaptiveConfig()
        )
        adaptive.start()

        # In main loop:
        while True:
            adaptive.check_and_act()
            time.sleep(60)
    """

    def __init__(
        self,
        strategy_name: str,
        freqtrade_client: Optional[FreqtradeClient] = None,
        version_control: Optional[StrategyVersionControl] = None,
        performance_db: Optional[PerformanceDB] = None,
        config: Optional[AdaptiveConfig] = None,
        state_file: str = "data/adaptive_state.json",
        strategy_deployer: Optional[StrategyDeployer] = None,
        rollback_manager: Optional[RollbackManager] = None,
    ):
        """
        Initialize adaptive optimizer.

        Args:
            strategy_name: Name of strategy to optimize
            freqtrade_client: Freqtrade API client
            version_control: Version control system
            performance_db: Performance database
            config: Adaptive optimization configuration
            state_file: Path to state persistence file
            strategy_deployer: Deployer configured with the real target strategy
                dir; without it the default container path is assumed
            rollback_manager: External rollback manager to reuse
        """
        self.strategy_name = strategy_name
        self.config = config or AdaptiveConfig()
        self.state_file = state_file

        # Initialize components
        self.client = freqtrade_client
        self.version_control = version_control or StrategyVersionControl()
        self.db = performance_db or PerformanceDB()

        # Create dependent components
        if self.client:
            self.monitor = PerformanceMonitor(
                self.client, self.db,
                snapshot_interval_minutes=self.config.check_interval_minutes,
                metrics_window_hours=self.config.metrics_window_hours
            )
        else:
            self.monitor = None

        self.detector = DegradationDetector(
            profit_threshold=1 - self.config.profit_decline_trigger,
            drawdown_threshold=self.config.drawdown_trigger,
            win_rate_threshold=self.config.win_rate_decline_trigger,
        )

        self.deployer = strategy_deployer or StrategyDeployer(self.version_control, self.client)
        self.rollback_manager = rollback_manager or RollbackManager(
            self.version_control,
            self.monitor,
            self.detector,
            RollbackConfig(
                enabled=self.config.auto_rollback_enabled,
                max_drawdown=self.config.drawdown_trigger
            )
        )
        # 让自动回滚真正恢复策略文件，而不是只改版本库状态
        self.rollback_manager.set_deploy_callback(self.deployer.rollback)

        # State
        self._state = AdaptiveState.IDLE
        self._last_optimization_time: Optional[datetime] = None
        self._optimization_history: List[OptimizationEvent] = []
        self._last_check_time: Optional[datetime] = None

        # Callbacks
        self._on_degradation_callback: Optional[Callable[[DetectionResult], None]] = None
        self._on_optimization_callback: Optional[Callable[[OptimizationEvent], None]] = None
        self._approval_callback: Optional[Callable[[str, Dict], bool]] = None
        self._optimization_func: Optional[Callable] = None

        # Load saved state
        self._load_state()

    def _load_state(self) -> None:
        """Load saved state from file."""
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            if data.get('last_optimization_time'):
                self._last_optimization_time = parse_utc(data['last_optimization_time'])

            for event_data in data.get('optimization_history', []):
                self._optimization_history.append(OptimizationEvent(
                    timestamp=parse_utc(event_data['timestamp']),
                    strategy_name=event_data['strategy_name'],
                    trigger_reason=event_data['trigger_reason'],
                    old_version=event_data['old_version'],
                    new_version=event_data['new_version'],
                    success=event_data['success'],
                    improvement_pct=event_data['improvement_pct'],
                    notes=event_data.get('notes', ''),
                ))

        except Exception as e:
            logger.error(f"Error loading adaptive state: {e}")

    def _save_state(self) -> None:
        """Save state to file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        data = {
            'strategy_name': self.strategy_name,
            'state': self._state.value,
            'last_optimization_time': self._last_optimization_time.isoformat() if self._last_optimization_time else None,
            'optimization_history': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'strategy_name': e.strategy_name,
                    'trigger_reason': e.trigger_reason,
                    'old_version': e.old_version,
                    'new_version': e.new_version,
                    'success': e.success,
                    'improvement_pct': e.improvement_pct,
                    'notes': e.notes,
                }
                for e in self._optimization_history[-50:]  # Keep last 50
            ]
        }

        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_callbacks(
        self,
        on_degradation: Optional[Callable[[DetectionResult], None]] = None,
        on_optimization: Optional[Callable[[OptimizationEvent], None]] = None,
        approval: Optional[Callable[[str, Dict], bool]] = None,
        optimization_func: Optional[Callable] = None
    ) -> None:
        """
        Set callback functions.

        Args:
            on_degradation: Called when degradation is detected
            on_optimization: Called after optimization completes
            approval: Called to get approval for deployment
            optimization_func: Custom optimization function
        """
        self._on_degradation_callback = on_degradation
        self._on_optimization_callback = on_optimization
        self._approval_callback = approval
        self._optimization_func = optimization_func

    @property
    def state(self) -> AdaptiveState:
        """Get current state."""
        return self._state

    def start(self) -> None:
        """Start the adaptive optimization system."""
        self._state = AdaptiveState.MONITORING
        logger.info(f"Adaptive optimizer started for {self.strategy_name}")

    def stop(self) -> None:
        """Stop the adaptive optimization system."""
        self._state = AdaptiveState.IDLE
        self._save_state()
        logger.info(f"Adaptive optimizer stopped for {self.strategy_name}")

    def check_and_act(self) -> Optional[AdaptiveState]:
        """
        Main check loop - call this periodically.

        Returns:
            Current state after check
        """
        if self._state == AdaptiveState.IDLE:
            return self._state

        now = utc_now()

        # Check interval
        if self._last_check_time:
            elapsed = (now - self._last_check_time).total_seconds() / 60
            if elapsed < self.config.check_interval_minutes:
                return self._state

        self._last_check_time = now

        try:
            if self._state == AdaptiveState.MONITORING:
                return self._check_monitoring()

            elif self._state == AdaptiveState.DEGRADATION_DETECTED:
                return self._handle_degradation()

            elif self._state == AdaptiveState.COOLDOWN:
                return self._check_cooldown()

        except Exception as e:
            logger.error(f"Error in adaptive check: {e}")
            self._state = AdaptiveState.ERROR

        return self._state

    def _check_monitoring(self) -> AdaptiveState:
        """Check for degradation during monitoring."""
        # Collect performance data
        if self.monitor:
            self.monitor.collect_and_store()

        # Get recent snapshots
        snapshots = self.db.get_rolling_metrics(
            self.strategy_name,
            window_hours=self.config.metrics_window_hours
        )

        if len(snapshots) < 5:
            logger.debug("Insufficient data for degradation detection")
            return AdaptiveState.MONITORING

        # Get baseline
        baseline = self.db.get_latest_baseline(self.strategy_name)

        # Detect degradation
        result = self.detector.detect(snapshots, baseline)

        if result.is_degraded:
            logger.warning(f"Degradation detected: score={result.degradation_score:.2f}")

            if self._on_degradation_callback:
                self._on_degradation_callback(result)

            self._state = AdaptiveState.DEGRADATION_DETECTED
            return self._state

        return AdaptiveState.MONITORING

    def _handle_degradation(self) -> AdaptiveState:
        """Handle detected degradation."""
        # Check if we can optimize
        if not self._can_optimize():
            logger.info("Cannot optimize yet (rate limit or cooldown)")
            self._state = AdaptiveState.COOLDOWN
            return self._state

        # Check if enough trades
        if self.monitor:
            metrics = self.monitor.get_current_metrics()
            if metrics.total_trades < self.config.min_trades_for_evaluation:
                logger.info(f"Not enough trades for optimization: {metrics.total_trades}")
                self._state = AdaptiveState.MONITORING
                return self._state

        # Trigger optimization
        logger.info("Triggering re-optimization")
        self._state = AdaptiveState.OPTIMIZING

        success = self._run_optimization()

        if success:
            self._state = AdaptiveState.MONITORING
        else:
            self._state = AdaptiveState.COOLDOWN

        return self._state

    def _can_optimize(self) -> bool:
        """Check if optimization is allowed."""
        # Check time since last optimization
        if self._last_optimization_time:
            hours_since = (utc_now() - self._last_optimization_time).total_seconds() / 3600
            if hours_since < self.config.min_hours_between_optimizations:
                return False

        # Check weekly limit
        week_ago = utc_now() - timedelta(days=7)
        recent_optimizations = sum(
            1 for e in self._optimization_history
            if e.timestamp > week_ago
        )

        if recent_optimizations >= self.config.max_optimizations_per_week:
            return False

        return True

    def _run_optimization(self) -> bool:
        """Run the optimization process."""
        old_version = self.version_control.get_active_version(self.strategy_name)
        old_version_id = old_version.version_id if old_version else "none"

        try:
            # Run optimization (using callback or default)
            if self._optimization_func:
                result = self._optimization_func(
                    self.strategy_name,
                    self.config.optimization_days,
                    self.config.recent_data_weight
                )

                if not result or not result.get('success'):
                    logger.error("Optimization failed")
                    return False

                new_params = result.get('parameters', {})
                new_metrics = result.get('metrics', {})

            else:
                # Placeholder - in real implementation, integrate with GA/Optuna
                logger.warning("No optimization function set, using placeholder")
                new_params = {}
                new_metrics = {}

            # Create new version
            # This would create the actual strategy file in real implementation
            new_version = self.version_control.create_version(
                strategy_name=self.strategy_name,
                source_file=old_version.file_path if old_version else "",
                parameters=new_params,
                backtest_metrics=new_metrics,
                parent_version=old_version_id,
                notes="Auto-generated by adaptive optimizer"
            )

            # Check improvement
            old_profit = old_version.backtest_metrics.get('total_profit_pct', 0) if old_version else 0
            new_profit = new_metrics.get('total_profit_pct', 0)
            improvement = (new_profit - old_profit) / abs(old_profit) if old_profit else 0

            # Check approval
            if self.config.require_approval:
                if self._approval_callback:
                    approved = self._approval_callback(
                        new_version.version_id,
                        {'improvement': improvement, 'metrics': new_metrics}
                    )
                else:
                    logger.info("Optimization requires approval but no approval callback is set")
                    approved = False
            else:
                approved = True

            if not approved:
                logger.info("Optimization not approved")
                return False

            # Deploy
            deploy_config = DeploymentConfig(
                shadow_trading_hours=self.config.shadow_trading_hours,
                gradual_rollout=self.config.gradual_rollout,
                require_approval=False  # Already approved
            )

            result = self.deployer.deploy(
                self.strategy_name,
                new_version.version_id,
                deploy_config
            )

            success = result.status.value == "completed"

            # Record event
            event = OptimizationEvent(
                timestamp=utc_now(),
                strategy_name=self.strategy_name,
                trigger_reason="degradation_detected",
                old_version=old_version_id,
                new_version=new_version.version_id,
                success=success,
                improvement_pct=improvement * 100,
            )

            self._optimization_history.append(event)
            self._last_optimization_time = utc_now()
            self._save_state()

            if self._on_optimization_callback:
                self._on_optimization_callback(event)

            # Save new baseline
            if success:
                self.db.save_baseline(self.strategy_name, new_metrics)

            return success

        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return False

    def _check_cooldown(self) -> AdaptiveState:
        """Check if cooldown period is over."""
        if self._can_optimize():
            self._state = AdaptiveState.MONITORING

        return self._state

    def force_optimization(self, reason: str = "manual") -> bool:
        """
        Force an immediate optimization.

        Args:
            reason: Reason for forcing optimization

        Returns:
            True if optimization was successful
        """
        logger.info(f"Forcing optimization: {reason}")
        self._state = AdaptiveState.OPTIMIZING
        return self._run_optimization()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the adaptive optimizer."""
        return {
            'strategy_name': self.strategy_name,
            'state': self._state.value,
            'last_optimization': self._last_optimization_time.isoformat() if self._last_optimization_time else None,
            'can_optimize': self._can_optimize(),
            'optimization_count_this_week': sum(
                1 for e in self._optimization_history
                if e.timestamp > utc_now() - timedelta(days=7)
            ),
            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
        }

    def get_optimization_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent optimization history."""
        events = self._optimization_history[-limit:]
        return [
            {
                'timestamp': e.timestamp.isoformat(),
                'trigger_reason': e.trigger_reason,
                'old_version': e.old_version,
                'new_version': e.new_version,
                'success': e.success,
                'improvement_pct': e.improvement_pct,
            }
            for e in reversed(events)
        ]

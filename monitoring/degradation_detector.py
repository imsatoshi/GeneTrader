"""
Strategy degradation detection using statistical methods.

This module provides detection of strategy performance degradation
using Statistical Process Control (SPC), CUSUM charts, and market
regime detection.
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from utils.logging_config import logger

from monitoring.performance_db import PerformanceSnapshot


class AlertSeverity(Enum):
    """Severity levels for degradation alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of degradation alerts."""
    PROFIT_DECLINE = "profit_decline"
    WIN_RATE_DROP = "win_rate_drop"
    DRAWDOWN_INCREASE = "drawdown_increase"
    TRADE_FREQUENCY_DROP = "trade_frequency_drop"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    VOLATILITY_SPIKE = "volatility_spike"
    MARKET_REGIME_CHANGE = "market_regime_change"
    STATISTICAL_DEVIATION = "statistical_deviation"


class MarketRegime(Enum):
    """Market regime classifications."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


@dataclass
class DegradationAlert:
    """Alert for detected degradation."""
    timestamp: datetime
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'current_value': self.current_value,
            'baseline_value': self.baseline_value,
            'threshold': self.threshold,
            'details': self.details,
        }


@dataclass
class DetectionResult:
    """Result of degradation detection."""
    is_degraded: bool
    degradation_score: float  # 0-1, higher = more degraded
    alerts: List[DegradationAlert]
    market_regime: MarketRegime
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)


class DegradationDetector:
    """
    Detects strategy performance degradation using statistical methods.

    Methods:
    - Statistical Process Control (SPC): Control charts for process monitoring
    - CUSUM: Cumulative sum control chart for detecting shifts
    - Market Regime Detection: Classifies current market conditions

    Triggers:
    - Profit falls below threshold vs baseline
    - Win rate drops significantly
    - Drawdown exceeds limit
    - Trade frequency drops
    - Statistical deviation from baseline
    """

    def __init__(
        self,
        profit_threshold: float = 0.7,  # Live profit should be at least 70% of baseline
        win_rate_threshold: float = 0.15,  # Max 15% win rate drop
        drawdown_threshold: float = 0.35,  # Max drawdown
        drawdown_increase_threshold: float = 1.5,  # Max 50% increase vs baseline
        frequency_threshold: float = 0.5,  # Min 50% of baseline trade frequency
        consecutive_loss_limit: int = 5,
        cusum_threshold: float = 3.0,  # Standard deviations for CUSUM alert
        lookback_periods: int = 20,  # Periods for baseline calculation
    ):
        """
        Initialize degradation detector.

        Args:
            profit_threshold: Minimum acceptable profit ratio vs baseline
            win_rate_threshold: Maximum acceptable win rate drop
            drawdown_threshold: Maximum acceptable drawdown
            drawdown_increase_threshold: Maximum drawdown increase vs baseline
            frequency_threshold: Minimum trade frequency ratio vs baseline
            consecutive_loss_limit: Max consecutive losses before alert
            cusum_threshold: CUSUM threshold in standard deviations
            lookback_periods: Number of periods for baseline calculation
        """
        self.profit_threshold = profit_threshold
        self.win_rate_threshold = win_rate_threshold
        self.drawdown_threshold = drawdown_threshold
        self.drawdown_increase_threshold = drawdown_increase_threshold
        self.frequency_threshold = frequency_threshold
        self.consecutive_loss_limit = consecutive_loss_limit
        self.cusum_threshold = cusum_threshold
        self.lookback_periods = lookback_periods

        # CUSUM state
        self._cusum_positive = 0.0
        self._cusum_negative = 0.0
        self._cusum_baseline: Optional[float] = None
        self._cusum_std: Optional[float] = None

    def detect(
        self,
        snapshots: List[PerformanceSnapshot],
        baseline: Optional[Dict[str, Any]] = None
    ) -> DetectionResult:
        """
        Detect degradation from performance snapshots.

        Args:
            snapshots: Recent performance snapshots (newest first)
            baseline: Backtest baseline metrics

        Returns:
            DetectionResult with alerts and recommendations
        """
        alerts: List[DegradationAlert] = []

        if not snapshots:
            return DetectionResult(
                is_degraded=False,
                degradation_score=0.0,
                alerts=[],
                market_regime=MarketRegime.UNKNOWN,
                recommendation="Insufficient data for detection"
            )

        # Get latest snapshot
        latest = snapshots[0]

        # Get baseline from history if not provided
        if not baseline and len(snapshots) >= self.lookback_periods:
            baseline = self._calculate_baseline_from_history(snapshots)

        # Run detection checks
        if baseline:
            # Profit check
            profit_alert = self._check_profit(latest, baseline)
            if profit_alert:
                alerts.append(profit_alert)

            # Win rate check
            win_rate_alert = self._check_win_rate(latest, baseline)
            if win_rate_alert:
                alerts.append(win_rate_alert)

            # Drawdown check
            drawdown_alert = self._check_drawdown(latest, baseline)
            if drawdown_alert:
                alerts.append(drawdown_alert)

            # Trade frequency check
            freq_alert = self._check_trade_frequency(latest, baseline)
            if freq_alert:
                alerts.append(freq_alert)

        # CUSUM check (statistical process control)
        if len(snapshots) >= self.lookback_periods:
            cusum_alert = self._check_cusum(snapshots)
            if cusum_alert:
                alerts.append(cusum_alert)

        # Volatility check
        if len(snapshots) >= 5:
            vol_alert = self._check_volatility(snapshots)
            if vol_alert:
                alerts.append(vol_alert)

        # Detect market regime
        market_regime = self._detect_market_regime(snapshots)

        # Calculate overall degradation score
        degradation_score = self._calculate_degradation_score(alerts)
        is_degraded = degradation_score >= 0.5 or any(
            a.severity == AlertSeverity.CRITICAL for a in alerts
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(alerts, is_degraded, market_regime)

        return DetectionResult(
            is_degraded=is_degraded,
            degradation_score=degradation_score,
            alerts=alerts,
            market_regime=market_regime,
            recommendation=recommendation,
            details={
                'num_alerts': len(alerts),
                'critical_alerts': sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL),
                'warning_alerts': sum(1 for a in alerts if a.severity == AlertSeverity.WARNING),
            }
        )

    def _calculate_baseline_from_history(
        self,
        snapshots: List[PerformanceSnapshot]
    ) -> Dict[str, Any]:
        """Calculate baseline from historical snapshots."""
        # Use older snapshots as baseline (skip recent ones)
        baseline_snapshots = snapshots[self.lookback_periods // 2:]

        if not baseline_snapshots:
            return {}

        return {
            'total_profit_pct': statistics.mean(s.total_profit_pct for s in baseline_snapshots),
            'win_rate': statistics.mean(s.win_rate for s in baseline_snapshots),
            'max_drawdown': statistics.mean(s.max_drawdown for s in baseline_snapshots),
            'avg_trades_per_day': statistics.mean(
                s.extra_data.get('trades_per_day', 0) if s.extra_data else 0
                for s in baseline_snapshots
            ),
        }

    def _check_profit(
        self,
        latest: PerformanceSnapshot,
        baseline: Dict[str, Any]
    ) -> Optional[DegradationAlert]:
        """Check if profit has degraded."""
        baseline_profit = baseline.get('total_profit_pct', 0)
        if baseline_profit <= 0:
            return None

        profit_ratio = latest.total_profit_pct / baseline_profit

        if profit_ratio < self.profit_threshold:
            severity = AlertSeverity.CRITICAL if profit_ratio < 0.5 else AlertSeverity.WARNING
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.PROFIT_DECLINE,
                severity=severity,
                message=f"Profit at {profit_ratio:.1%} of baseline ({latest.total_profit_pct:.2%} vs {baseline_profit:.2%})",
                current_value=latest.total_profit_pct,
                baseline_value=baseline_profit,
                threshold=self.profit_threshold,
                details={'profit_ratio': profit_ratio}
            )
        return None

    def _check_win_rate(
        self,
        latest: PerformanceSnapshot,
        baseline: Dict[str, Any]
    ) -> Optional[DegradationAlert]:
        """Check if win rate has dropped."""
        baseline_win_rate = baseline.get('win_rate', 0.5)
        win_rate_drop = baseline_win_rate - latest.win_rate

        if win_rate_drop > self.win_rate_threshold:
            severity = AlertSeverity.CRITICAL if win_rate_drop > 0.25 else AlertSeverity.WARNING
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.WIN_RATE_DROP,
                severity=severity,
                message=f"Win rate dropped by {win_rate_drop:.1%} ({latest.win_rate:.1%} vs {baseline_win_rate:.1%})",
                current_value=latest.win_rate,
                baseline_value=baseline_win_rate,
                threshold=self.win_rate_threshold,
                details={'win_rate_drop': win_rate_drop}
            )
        return None

    def _check_drawdown(
        self,
        latest: PerformanceSnapshot,
        baseline: Dict[str, Any]
    ) -> Optional[DegradationAlert]:
        """Check if drawdown has increased."""
        # Absolute drawdown check
        if latest.max_drawdown > self.drawdown_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.DRAWDOWN_INCREASE,
                severity=AlertSeverity.CRITICAL,
                message=f"Drawdown {latest.max_drawdown:.1%} exceeds threshold {self.drawdown_threshold:.1%}",
                current_value=latest.max_drawdown,
                baseline_value=baseline.get('max_drawdown', 0),
                threshold=self.drawdown_threshold,
            )

        # Relative drawdown check
        baseline_dd = baseline.get('max_drawdown', 0.1) or 0.1
        dd_ratio = latest.max_drawdown / baseline_dd

        if dd_ratio > self.drawdown_increase_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.DRAWDOWN_INCREASE,
                severity=AlertSeverity.WARNING,
                message=f"Drawdown increased to {dd_ratio:.1f}x baseline ({latest.max_drawdown:.1%} vs {baseline_dd:.1%})",
                current_value=latest.max_drawdown,
                baseline_value=baseline_dd,
                threshold=self.drawdown_increase_threshold,
                details={'drawdown_ratio': dd_ratio}
            )
        return None

    def _check_trade_frequency(
        self,
        latest: PerformanceSnapshot,
        baseline: Dict[str, Any]
    ) -> Optional[DegradationAlert]:
        """Check if trade frequency has dropped."""
        baseline_freq = baseline.get('avg_trades_per_day', 1.0)
        if not baseline_freq or baseline_freq <= 0:
            return None

        current_freq = latest.extra_data.get('trades_per_day', 0) if latest.extra_data else 0
        freq_ratio = current_freq / baseline_freq

        if freq_ratio < self.frequency_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.TRADE_FREQUENCY_DROP,
                severity=AlertSeverity.WARNING,
                message=f"Trade frequency at {freq_ratio:.1%} of baseline ({current_freq:.1f}/day vs {baseline_freq:.1f}/day)",
                current_value=current_freq,
                baseline_value=baseline_freq,
                threshold=self.frequency_threshold,
                details={'frequency_ratio': freq_ratio}
            )
        return None

    def _check_cusum(
        self,
        snapshots: List[PerformanceSnapshot]
    ) -> Optional[DegradationAlert]:
        """
        CUSUM (Cumulative Sum) control chart for detecting shifts.

        Detects sustained shifts in performance that may not be obvious
        from individual data points.
        """
        if len(snapshots) < self.lookback_periods:
            return None

        # Get profit values
        profits = [s.total_profit_pct for s in snapshots]

        # Calculate baseline mean and std from historical data
        historical = profits[self.lookback_periods // 2:]
        if len(historical) < 5:
            return None

        mean = statistics.mean(historical)
        std = statistics.stdev(historical) if len(historical) >= 2 else 0.01
        if std == 0:
            std = 0.01

        # Update CUSUM state
        self._cusum_baseline = mean
        self._cusum_std = std

        # Calculate CUSUM for recent values
        # profits are newest-first; CUSUM must accumulate in chronological order
        recent = list(reversed(profits[:self.lookback_periods // 2]))
        cusum_pos = 0.0
        cusum_neg = 0.0
        slack = 0.5 * std  # Slack parameter

        for val in recent:
            deviation = val - mean
            cusum_pos = max(0, cusum_pos + deviation - slack)
            cusum_neg = min(0, cusum_neg + deviation + slack)

        # Check if CUSUM exceeds threshold
        threshold_value = self.cusum_threshold * std

        if cusum_neg < -threshold_value:
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.STATISTICAL_DEVIATION,
                severity=AlertSeverity.WARNING,
                message=f"CUSUM detected negative shift: {cusum_neg / std:.1f} standard deviations",
                current_value=cusum_neg,
                baseline_value=mean,
                threshold=threshold_value,
                details={
                    'cusum_value': cusum_neg,
                    'std_deviations': cusum_neg / std,
                    'baseline_mean': mean,
                    'baseline_std': std,
                }
            )

        return None

    def _check_volatility(
        self,
        snapshots: List[PerformanceSnapshot]
    ) -> Optional[DegradationAlert]:
        """Check for volatility spikes in returns."""
        if len(snapshots) < 5:
            return None

        # Calculate rolling volatility
        recent_profits = [s.total_profit_pct for s in snapshots[:5]]
        historical_profits = [s.total_profit_pct for s in snapshots[5:]]

        if len(historical_profits) < 5:
            return None

        recent_std = statistics.stdev(recent_profits) if len(recent_profits) >= 2 else 0
        historical_std = statistics.stdev(historical_profits) if len(historical_profits) >= 2 else 0.01

        if historical_std == 0:
            historical_std = 0.01

        vol_ratio = recent_std / historical_std

        if vol_ratio > 2.0:  # Volatility doubled
            return DegradationAlert(
                timestamp=datetime.now(),
                alert_type=AlertType.VOLATILITY_SPIKE,
                severity=AlertSeverity.INFO,
                message=f"Volatility increased to {vol_ratio:.1f}x historical",
                current_value=recent_std,
                baseline_value=historical_std,
                threshold=2.0,
                details={'volatility_ratio': vol_ratio}
            )

        return None

    def _detect_market_regime(
        self,
        snapshots: List[PerformanceSnapshot]
    ) -> MarketRegime:
        """Detect current market regime from performance patterns."""
        if len(snapshots) < 5:
            return MarketRegime.UNKNOWN

        # Analyze recent profit trend
        recent = snapshots[:5]
        profits = [s.total_profit_pct for s in recent]

        avg_profit = statistics.mean(profits)
        profit_std = statistics.stdev(profits) if len(profits) >= 2 else 0

        # Classify regime
        if profit_std > 0.1:  # High variance
            return MarketRegime.HIGH_VOLATILITY
        elif profit_std < 0.02:  # Low variance
            return MarketRegime.LOW_VOLATILITY
        elif avg_profit > 0.05:
            return MarketRegime.BULLISH
        elif avg_profit < -0.05:
            return MarketRegime.BEARISH
        else:
            return MarketRegime.SIDEWAYS

    def _calculate_degradation_score(self, alerts: List[DegradationAlert]) -> float:
        """Calculate overall degradation score from alerts."""
        if not alerts:
            return 0.0

        # Weight by severity
        severity_weights = {
            AlertSeverity.INFO: 0.1,
            AlertSeverity.WARNING: 0.3,
            AlertSeverity.CRITICAL: 0.5,
        }

        total_weight = sum(severity_weights[a.severity] for a in alerts)

        # Normalize to 0-1 range
        return min(1.0, total_weight)

    def _generate_recommendation(
        self,
        alerts: List[DegradationAlert],
        is_degraded: bool,
        market_regime: MarketRegime
    ) -> str:
        """Generate recommendation based on detection results."""
        if not alerts:
            return "Strategy performing within acceptable parameters. Continue monitoring."

        if not is_degraded:
            return f"Minor alerts detected. Market regime: {market_regime.value}. Continue monitoring closely."

        # Check for critical alerts
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]

        if critical:
            if any(a.alert_type == AlertType.DRAWDOWN_INCREASE for a in critical):
                return "CRITICAL: Drawdown exceeds threshold. Consider pausing trading and reviewing strategy."
            if any(a.alert_type == AlertType.PROFIT_DECLINE for a in critical):
                return "CRITICAL: Significant profit decline. Consider triggering re-optimization."

        # General degradation
        return f"Strategy degradation detected ({len(alerts)} alerts). Market: {market_regime.value}. Consider re-optimization."

    def reset_cusum(self) -> None:
        """Reset CUSUM state for fresh detection."""
        self._cusum_positive = 0.0
        self._cusum_negative = 0.0
        self._cusum_baseline = None
        self._cusum_std = None

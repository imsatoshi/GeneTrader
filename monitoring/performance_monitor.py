"""
Performance monitoring for live trading strategies.

This module provides real-time performance tracking, metrics calculation,
and comparison with backtest baselines.
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from typing import Any, Dict, List, Optional, Tuple
from utils.logging_config import logger

from monitoring.freqtrade_client import FreqtradeClient, Trade
from monitoring.performance_db import PerformanceDB, PerformanceSnapshot, TradeRecord


@dataclass
class PerformanceMetrics:
    """Calculated performance metrics."""
    total_profit: float = 0.0
    total_profit_pct: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_profit_per_trade: float = 0.0
    avg_duration_minutes: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    expectancy: float = 0.0
    trades_per_day: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_winning_trade: float = 0.0
    avg_losing_trade: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0


@dataclass
class ComparisonResult:
    """Result of comparing live performance to backtest baseline."""
    live_metrics: PerformanceMetrics
    baseline_metrics: Dict[str, Any]
    profit_ratio: float  # live_profit / baseline_profit
    win_rate_diff: float  # live_win_rate - baseline_win_rate
    drawdown_ratio: float  # live_drawdown / baseline_drawdown
    trade_frequency_ratio: float  # live_trades_per_day / baseline_trades_per_day
    is_degraded: bool
    degradation_score: float  # 0-1, higher = more degraded
    details: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Real-time performance monitoring for live trading.

    Collects live trading data from Freqtrade, calculates performance metrics,
    stores historical data, and compares against backtest baselines.
    """

    def __init__(
        self,
        client: FreqtradeClient,
        db: PerformanceDB,
        snapshot_interval_minutes: int = 5,
        metrics_window_hours: int = 168,  # 7 days
        degradation_threshold: float = 0.7
    ):
        """
        Initialize performance monitor.

        Args:
            client: FreqtradeClient instance
            db: PerformanceDB instance
            snapshot_interval_minutes: Interval between snapshots
            metrics_window_hours: Window for rolling metrics calculation
            degradation_threshold: Threshold for degradation detection (0-1)
        """
        self.client = client
        self.db = db
        self.snapshot_interval_minutes = snapshot_interval_minutes
        self.metrics_window_hours = metrics_window_hours
        self.degradation_threshold = degradation_threshold

        self._last_snapshot_time: Optional[datetime] = None
        self._cached_metrics: Optional[PerformanceMetrics] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60

    def collect_and_store(self) -> Optional[PerformanceSnapshot]:
        """
        Collect current performance data and store snapshot.

        Returns:
            PerformanceSnapshot if collected, None if too soon since last snapshot
        """
        now = utc_now()

        # Check if we should collect
        if self._last_snapshot_time:
            elapsed = (now - self._last_snapshot_time).total_seconds() / 60
            if elapsed < self.snapshot_interval_minutes:
                return None

        try:
            # Get system status
            status = self.client.get_status()
            strategy_name = status.strategy

            # Get trades and calculate metrics
            since = now - timedelta(hours=self.metrics_window_hours)
            trades = self.client.get_trades_since(since)

            # Store new trades
            for trade in trades:
                if trade.close_date:
                    duration = int((trade.close_date - trade.open_date).total_seconds() / 60)
                    self.db.save_trade(TradeRecord(
                        trade_id=trade.trade_id,
                        pair=trade.pair,
                        open_date=trade.open_date,
                        close_date=trade.close_date,
                        open_rate=trade.open_rate,
                        close_rate=trade.close_rate or 0,
                        profit_ratio=trade.profit_ratio,
                        profit_abs=trade.profit_abs,
                        stake_amount=trade.stake_amount,
                        duration_minutes=duration,
                        strategy=trade.strategy or strategy_name,
                        is_short=trade.is_short,
                    ))

            # Calculate metrics
            metrics = self.calculate_metrics(trades)

            # Get balance
            try:
                balances = self.client.get_balance()
                total_balance = sum(b.total for b in balances.values())
            except Exception:
                total_balance = 0.0

            # Create snapshot
            snapshot = PerformanceSnapshot(
                timestamp=now,
                strategy_name=strategy_name,
                total_profit=metrics.total_profit,
                total_profit_pct=metrics.total_profit_pct,
                win_rate=metrics.win_rate,
                total_trades=metrics.total_trades,
                winning_trades=metrics.winning_trades,
                losing_trades=metrics.losing_trades,
                avg_profit_per_trade=metrics.avg_profit_per_trade,
                avg_duration_minutes=metrics.avg_duration_minutes,
                max_drawdown=metrics.max_drawdown,
                profit_factor=metrics.profit_factor,
                sharpe_ratio=metrics.sharpe_ratio,
                sortino_ratio=metrics.sortino_ratio,
                expectancy=metrics.expectancy,
                open_trades=len([t for t in trades if t.is_open]),
                balance=total_balance,
                extra_data={
                    'trades_per_day': metrics.trades_per_day,
                    'best_trade': metrics.best_trade,
                    'worst_trade': metrics.worst_trade,
                }
            )

            # Save to database
            self.db.save_snapshot(snapshot)
            self._last_snapshot_time = now

            logger.info(f"Collected performance snapshot: {metrics.total_trades} trades, "
                       f"win rate {metrics.win_rate:.2%}, profit {metrics.total_profit_pct:.2%}")

            return snapshot

        except Exception as e:
            logger.error(f"Error collecting performance data: {e}")
            return None

    def calculate_metrics(self, trades: List[Trade]) -> PerformanceMetrics:
        """
        Calculate performance metrics from a list of trades.

        Args:
            trades: List of Trade objects

        Returns:
            PerformanceMetrics with calculated values
        """
        metrics = PerformanceMetrics()

        # Filter closed trades
        closed_trades = [t for t in trades if t.close_date and not t.is_open]

        if not closed_trades:
            return metrics

        metrics.total_trades = len(closed_trades)

        # Profit calculations
        profits = [t.profit_ratio for t in closed_trades]
        abs_profits = [t.profit_abs for t in closed_trades]

        metrics.total_profit = sum(abs_profits)
        metrics.total_profit_pct = sum(profits)
        metrics.avg_profit_per_trade = statistics.mean(profits) if profits else 0

        # Win/Loss breakdown
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]

        metrics.winning_trades = len(winning)
        metrics.losing_trades = len(losing)
        metrics.win_rate = len(winning) / len(profits) if profits else 0

        metrics.avg_winning_trade = statistics.mean(winning) if winning else 0
        metrics.avg_losing_trade = statistics.mean(losing) if losing else 0
        metrics.best_trade = max(profits) if profits else 0
        metrics.worst_trade = min(profits) if profits else 0

        # Duration
        durations = []
        for t in closed_trades:
            if t.close_date:
                duration = (t.close_date - t.open_date).total_seconds() / 60
                durations.append(duration)
        metrics.avg_duration_minutes = statistics.mean(durations) if durations else 0

        # Profit factor
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Drawdown calculation
        metrics.max_drawdown = self._calculate_max_drawdown(closed_trades)

        # Sharpe and Sortino ratios
        if len(profits) >= 2:
            try:
                mean_return = statistics.mean(profits)
                std_return = statistics.stdev(profits)
                if std_return > 0:
                    # Annualized (assuming 365 trades per year)
                    metrics.sharpe_ratio = (mean_return / std_return) * math.sqrt(365)

                # Sortino (using downside deviation)
                downside_returns = [p for p in profits if p < 0]
                if downside_returns:
                    downside_std = statistics.stdev(downside_returns) if len(downside_returns) >= 2 else abs(downside_returns[0])
                    if downside_std > 0:
                        metrics.sortino_ratio = (mean_return / downside_std) * math.sqrt(365)
            except Exception:
                pass

        # Expectancy
        avg_win = abs(metrics.avg_winning_trade)
        avg_loss = abs(metrics.avg_losing_trade)
        if avg_loss > 0:
            metrics.expectancy = (metrics.win_rate * avg_win) - ((1 - metrics.win_rate) * avg_loss)

        # Trades per day
        if closed_trades:
            first_trade = min(t.open_date for t in closed_trades)
            last_trade = max(t.close_date for t in closed_trades if t.close_date)
            days = max(1, (last_trade - first_trade).days)
            metrics.trades_per_day = len(closed_trades) / days

        # Consecutive wins/losses
        metrics.max_consecutive_wins, metrics.max_consecutive_losses = \
            self._calculate_consecutive_streaks(profits)

        return metrics

    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown from trade list."""
        if not trades:
            return 0.0

        # Sort by close date
        sorted_trades = sorted(trades, key=lambda t: t.close_date or t.open_date)

        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in sorted_trades:
            cumulative += trade.profit_ratio
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def _calculate_consecutive_streaks(self, profits: List[float]) -> Tuple[int, int]:
        """Calculate max consecutive wins and losses."""
        if not profits:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for p in profits:
            if p > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif p < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0

        return max_wins, max_losses

    def get_current_metrics(self, force_refresh: bool = False) -> PerformanceMetrics:
        """
        Get current performance metrics (cached).

        Args:
            force_refresh: Force recalculation

        Returns:
            Current PerformanceMetrics
        """
        now = utc_now()

        # Check cache
        if not force_refresh and self._cached_metrics and self._cache_time:
            if (now - self._cache_time).total_seconds() < self._cache_ttl_seconds:
                return self._cached_metrics

        # Fetch and calculate
        since = now - timedelta(hours=self.metrics_window_hours)
        trades = self.client.get_trades_since(since)
        metrics = self.calculate_metrics(trades)

        # Update cache
        self._cached_metrics = metrics
        self._cache_time = now

        return metrics

    def compare_with_baseline(
        self,
        strategy_name: Optional[str] = None
    ) -> Optional[ComparisonResult]:
        """
        Compare current live performance with backtest baseline.

        Args:
            strategy_name: Strategy name (uses current if not specified)

        Returns:
            ComparisonResult or None if no baseline exists
        """
        # Get current metrics
        live_metrics = self.get_current_metrics()

        # Get strategy name
        if not strategy_name:
            try:
                status = self.client.get_status()
                strategy_name = status.strategy
            except Exception:
                return None

        # Get baseline
        baseline = self.db.get_latest_baseline(strategy_name)
        if not baseline:
            logger.warning(f"No baseline found for strategy {strategy_name}")
            return None

        # Calculate ratios
        baseline_profit = baseline.get('total_profit_pct', 0.01) or 0.01
        profit_ratio = live_metrics.total_profit_pct / baseline_profit if baseline_profit else 1.0

        baseline_win_rate = baseline.get('win_rate', 0.5) or 0.5
        win_rate_diff = live_metrics.win_rate - baseline_win_rate

        baseline_drawdown = baseline.get('max_drawdown', 0.1) or 0.1
        drawdown_ratio = live_metrics.max_drawdown / baseline_drawdown if baseline_drawdown else 1.0

        baseline_trades_per_day = baseline.get('avg_trades_per_day', 1.0) or 1.0
        trade_freq_ratio = live_metrics.trades_per_day / baseline_trades_per_day if baseline_trades_per_day else 1.0

        # Calculate degradation score (0-1, higher = worse)
        degradation_factors = []

        # Profit degradation (if significantly below baseline)
        if profit_ratio < 1.0:
            degradation_factors.append(1.0 - profit_ratio)

        # Win rate degradation
        if win_rate_diff < -0.05:  # 5% lower
            degradation_factors.append(min(1.0, abs(win_rate_diff) * 5))

        # Drawdown increase
        if drawdown_ratio > 1.5:  # 50% higher drawdown
            degradation_factors.append(min(1.0, (drawdown_ratio - 1) / 2))

        # Trade frequency drop
        if trade_freq_ratio < 0.5:  # Less than half the trades
            degradation_factors.append(1.0 - trade_freq_ratio)

        degradation_score = statistics.mean(degradation_factors) if degradation_factors else 0.0
        is_degraded = degradation_score >= self.degradation_threshold

        return ComparisonResult(
            live_metrics=live_metrics,
            baseline_metrics=baseline,
            profit_ratio=profit_ratio,
            win_rate_diff=win_rate_diff,
            drawdown_ratio=drawdown_ratio,
            trade_frequency_ratio=trade_freq_ratio,
            is_degraded=is_degraded,
            degradation_score=degradation_score,
            details={
                'profit_degradation': 1.0 - profit_ratio if profit_ratio < 1.0 else 0.0,
                'win_rate_degradation': abs(win_rate_diff) if win_rate_diff < 0 else 0.0,
                'drawdown_increase': drawdown_ratio - 1.0 if drawdown_ratio > 1.0 else 0.0,
                'frequency_drop': 1.0 - trade_freq_ratio if trade_freq_ratio < 1.0 else 0.0,
            }
        )

    def get_historical_metrics(
        self,
        hours: int = 168
    ) -> List[PerformanceSnapshot]:
        """
        Get historical performance snapshots.

        Args:
            hours: Number of hours to look back

        Returns:
            List of PerformanceSnapshot objects
        """
        since = utc_now() - timedelta(hours=hours)
        return self.db.get_snapshots(since=since)

    def save_backtest_baseline(
        self,
        strategy_name: str,
        metrics: Dict[str, Any],
        timerange: str = ""
    ) -> int:
        """
        Save backtest results as baseline for comparison.

        Args:
            strategy_name: Name of the strategy
            metrics: Backtest metrics dictionary
            timerange: Timerange used for backtest

        Returns:
            ID of saved baseline
        """
        return self.db.save_baseline(strategy_name, metrics, timerange)

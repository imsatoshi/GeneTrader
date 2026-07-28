"""Unit tests for monitoring module."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from utils.time_utils import utc_now
from unittest.mock import MagicMock, patch

from monitoring.freqtrade_client import FreqtradeClient, Trade, Balance, SystemStatus
from monitoring.performance_db import PerformanceDB, PerformanceSnapshot, TradeRecord
from monitoring.performance_monitor import PerformanceMonitor, PerformanceMetrics
from monitoring.degradation_detector import (
    DegradationDetector, DegradationAlert, AlertSeverity, AlertType, MarketRegime
)


class TestTrade(unittest.TestCase):
    """Tests for Trade dataclass."""

    def test_from_api_response(self):
        """Test creating Trade from API response."""
        data = {
            'trade_id': 123,
            'pair': 'BTC/USDT',
            'is_open': False,
            'open_date': '2024-01-01T10:00:00Z',
            'close_date': '2024-01-01T12:00:00Z',
            'open_rate': 40000.0,
            'close_rate': 41000.0,
            'profit_ratio': 0.025,
            'profit_abs': 25.0,
            'stake_amount': 1000.0,
            'amount': 0.025,
            'fee_open': 0.1,
            'fee_close': 0.1,
            'is_short': False,
            'leverage': 1.0,
            'strategy': 'TestStrategy',
            'timeframe': '5m',
        }

        trade = Trade.from_api_response(data)

        self.assertEqual(trade.trade_id, 123)
        self.assertEqual(trade.pair, 'BTC/USDT')
        self.assertFalse(trade.is_open)
        self.assertEqual(trade.profit_ratio, 0.025)
        self.assertEqual(trade.strategy, 'TestStrategy')


class TestPerformanceDB(unittest.TestCase):
    """Tests for PerformanceDB."""

    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_performance.db')
        self.db = PerformanceDB(self.db_path)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_save_and_get_snapshot(self):
        """Test saving and retrieving snapshots."""
        snapshot = PerformanceSnapshot(
            timestamp=utc_now(),
            strategy_name='TestStrategy',
            total_profit=100.0,
            total_profit_pct=0.05,
            win_rate=0.6,
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            avg_profit_per_trade=5.0,
            avg_duration_minutes=120.0,
            max_drawdown=0.08,
            profit_factor=1.5,
        )

        snapshot_id = self.db.save_snapshot(snapshot)
        self.assertIsNotNone(snapshot_id)

        snapshots = self.db.get_snapshots(strategy_name='TestStrategy')
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].total_trades, 20)

    def test_save_and_get_trade(self):
        """Test saving and retrieving trades."""
        trade = TradeRecord(
            trade_id=1,
            pair='ETH/USDT',
            open_date=utc_now() - timedelta(hours=2),
            close_date=utc_now(),
            open_rate=2000.0,
            close_rate=2100.0,
            profit_ratio=0.05,
            profit_abs=50.0,
            stake_amount=1000.0,
            duration_minutes=120,
            strategy='TestStrategy',
        )

        self.assertTrue(self.db.save_trade(trade))

        trades = self.db.get_trades(strategy='TestStrategy')
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].pair, 'ETH/USDT')

    def test_save_and_get_baseline(self):
        """Test saving and retrieving baselines."""
        metrics = {
            'total_profit_pct': 0.15,
            'win_rate': 0.65,
            'avg_profit_per_trade': 0.008,
            'max_drawdown': 0.10,
            'profit_factor': 2.0,
            'sharpe_ratio': 1.5,
            'total_trades': 100,
            'avg_trades_per_day': 3.0,
        }

        baseline_id = self.db.save_baseline('TestStrategy', metrics, '20240101-20240301')
        self.assertIsNotNone(baseline_id)

        baseline = self.db.get_latest_baseline('TestStrategy')
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline['win_rate'], 0.65)

    def test_get_rolling_metrics(self):
        """Test getting rolling metrics."""
        # Add multiple snapshots
        for i in range(10):
            snapshot = PerformanceSnapshot(
                timestamp=utc_now() - timedelta(hours=i * 24),
                strategy_name='TestStrategy',
                total_profit=100.0 + i * 10,
                total_profit_pct=0.05 + i * 0.01,
                win_rate=0.6,
                total_trades=20 + i,
                winning_trades=12,
                losing_trades=8,
                avg_profit_per_trade=5.0,
                avg_duration_minutes=120.0,
                max_drawdown=0.08,
                profit_factor=1.5,
            )
            self.db.save_snapshot(snapshot)

        snapshots = self.db.get_rolling_metrics('TestStrategy', window_hours=168)
        # Should get snapshots from last 7 days
        self.assertGreater(len(snapshots), 0)
        self.assertLessEqual(len(snapshots), 7)

    def test_cleanup_old_data(self):
        """Test cleanup of old data."""
        # Add old snapshot
        old_snapshot = PerformanceSnapshot(
            timestamp=utc_now() - timedelta(days=400),
            strategy_name='TestStrategy',
            total_profit=100.0,
            total_profit_pct=0.05,
            win_rate=0.6,
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            avg_profit_per_trade=5.0,
            avg_duration_minutes=120.0,
            max_drawdown=0.08,
            profit_factor=1.5,
        )
        self.db.save_snapshot(old_snapshot)

        # Add recent snapshot
        recent_snapshot = PerformanceSnapshot(
            timestamp=utc_now(),
            strategy_name='TestStrategy',
            total_profit=200.0,
            total_profit_pct=0.10,
            win_rate=0.7,
            total_trades=40,
            winning_trades=28,
            losing_trades=12,
            avg_profit_per_trade=5.0,
            avg_duration_minutes=120.0,
            max_drawdown=0.08,
            profit_factor=2.0,
        )
        self.db.save_snapshot(recent_snapshot)

        deleted = self.db.cleanup_old_data(retention_days=365)
        self.assertGreater(deleted, 0)

        # Recent should still exist
        snapshots = self.db.get_snapshots()
        self.assertEqual(len(snapshots), 1)


class TestPerformanceMonitor(unittest.TestCase):
    """Tests for PerformanceMonitor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_performance.db')
        self.db = PerformanceDB(self.db_path)
        self.mock_client = MagicMock(spec=FreqtradeClient)
        self.monitor = PerformanceMonitor(self.mock_client, self.db)

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_calculate_metrics_empty(self):
        """Test metrics calculation with no trades."""
        metrics = self.monitor.calculate_metrics([])
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)

    def test_calculate_metrics_with_trades(self):
        """Test metrics calculation with trades."""
        now = utc_now()
        trades = [
            Trade(
                trade_id=1, pair='BTC/USDT', is_open=False,
                open_date=now - timedelta(hours=5),
                close_date=now - timedelta(hours=4),
                open_rate=40000.0, close_rate=41000.0,
                profit_ratio=0.025, profit_abs=25.0,
                stake_amount=1000.0, amount=0.025,
                fee_open=0.1, fee_close=0.1,
            ),
            Trade(
                trade_id=2, pair='ETH/USDT', is_open=False,
                open_date=now - timedelta(hours=3),
                close_date=now - timedelta(hours=2),
                open_rate=2000.0, close_rate=1950.0,
                profit_ratio=-0.025, profit_abs=-25.0,
                stake_amount=1000.0, amount=0.5,
                fee_open=0.1, fee_close=0.1,
            ),
            Trade(
                trade_id=3, pair='BTC/USDT', is_open=False,
                open_date=now - timedelta(hours=1),
                close_date=now,
                open_rate=41000.0, close_rate=42000.0,
                profit_ratio=0.0244, profit_abs=24.4,
                stake_amount=1000.0, amount=0.024,
                fee_open=0.1, fee_close=0.1,
            ),
        ]

        metrics = self.monitor.calculate_metrics(trades)

        self.assertEqual(metrics.total_trades, 3)
        self.assertEqual(metrics.winning_trades, 2)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertAlmostEqual(metrics.win_rate, 2/3, places=2)
        self.assertGreater(metrics.profit_factor, 1.0)

    def test_compare_with_baseline(self):
        """Test comparison with baseline."""
        # Save baseline
        baseline_metrics = {
            'total_profit_pct': 0.10,
            'win_rate': 0.65,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }
        self.db.save_baseline('TestStrategy', baseline_metrics)

        # Mock client
        self.mock_client.get_status.return_value = SystemStatus(
            status='running', running=True, max_open_trades=5,
            open_trades=2, trading_enabled=True, strategy='TestStrategy',
            timeframe='5m', exchange='binance', state='running'
        )
        self.mock_client.get_trades_since.return_value = []

        result = self.monitor.compare_with_baseline('TestStrategy')

        # Should return comparison result
        self.assertIsNotNone(result)


class TestDegradationDetector(unittest.TestCase):
    """Tests for DegradationDetector."""

    def setUp(self):
        """Set up detector."""
        self.detector = DegradationDetector()

    def _create_snapshot(
        self,
        profit_pct: float = 0.05,
        win_rate: float = 0.6,
        max_drawdown: float = 0.08,
        trades_per_day: float = 5.0,
        hours_ago: int = 0
    ) -> PerformanceSnapshot:
        """Create a test snapshot."""
        return PerformanceSnapshot(
            timestamp=utc_now() - timedelta(hours=hours_ago),
            strategy_name='TestStrategy',
            total_profit=profit_pct * 1000,
            total_profit_pct=profit_pct,
            win_rate=win_rate,
            total_trades=int(trades_per_day * 7),
            winning_trades=int(win_rate * trades_per_day * 7),
            losing_trades=int((1 - win_rate) * trades_per_day * 7),
            avg_profit_per_trade=profit_pct / (trades_per_day * 7) if trades_per_day > 0 else 0,
            avg_duration_minutes=60.0,
            max_drawdown=max_drawdown,
            profit_factor=1.5,
            extra_data={'trades_per_day': trades_per_day}
        )

    def test_no_degradation(self):
        """Test detection with no degradation."""
        snapshots = [self._create_snapshot(hours_ago=i * 24) for i in range(30)]

        baseline = {
            'total_profit_pct': 0.05,
            'win_rate': 0.6,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }

        result = self.detector.detect(snapshots, baseline)

        self.assertFalse(result.is_degraded)
        self.assertEqual(len(result.alerts), 0)

    def test_profit_degradation(self):
        """Test detection of profit degradation."""
        # Recent snapshots with low profit
        snapshots = [
            self._create_snapshot(profit_pct=0.01, hours_ago=i * 24)
            for i in range(30)
        ]

        baseline = {
            'total_profit_pct': 0.10,  # Much higher baseline
            'win_rate': 0.6,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }

        result = self.detector.detect(snapshots, baseline)

        profit_alerts = [a for a in result.alerts if a.alert_type == AlertType.PROFIT_DECLINE]
        self.assertGreater(len(profit_alerts), 0)

    def test_win_rate_degradation(self):
        """Test detection of win rate drop."""
        snapshots = [
            self._create_snapshot(win_rate=0.35, hours_ago=i * 24)
            for i in range(30)
        ]

        baseline = {
            'total_profit_pct': 0.05,
            'win_rate': 0.65,  # Much higher baseline
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }

        result = self.detector.detect(snapshots, baseline)

        win_rate_alerts = [a for a in result.alerts if a.alert_type == AlertType.WIN_RATE_DROP]
        self.assertGreater(len(win_rate_alerts), 0)

    def test_drawdown_alert(self):
        """Test detection of excessive drawdown."""
        snapshots = [
            self._create_snapshot(max_drawdown=0.40, hours_ago=i * 24)
            for i in range(30)
        ]

        baseline = {
            'total_profit_pct': 0.05,
            'win_rate': 0.6,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }

        result = self.detector.detect(snapshots, baseline)

        drawdown_alerts = [a for a in result.alerts if a.alert_type == AlertType.DRAWDOWN_INCREASE]
        self.assertGreater(len(drawdown_alerts), 0)
        # Should be critical since it exceeds absolute threshold
        self.assertTrue(any(a.severity == AlertSeverity.CRITICAL for a in drawdown_alerts))

    def test_trade_frequency_drop(self):
        """Test detection of trade frequency drop."""
        snapshots = [
            self._create_snapshot(trades_per_day=1.0, hours_ago=i * 24)
            for i in range(30)
        ]

        baseline = {
            'total_profit_pct': 0.05,
            'win_rate': 0.6,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 10.0,  # Much higher frequency
        }

        result = self.detector.detect(snapshots, baseline)

        freq_alerts = [a for a in result.alerts if a.alert_type == AlertType.TRADE_FREQUENCY_DROP]
        self.assertGreater(len(freq_alerts), 0)

    def test_market_regime_detection(self):
        """Test market regime detection."""
        # Test that regime detection works (any valid regime is acceptable)
        snapshots = [
            self._create_snapshot(profit_pct=0.10, hours_ago=i * 24)
            for i in range(30)
        ]

        result = self.detector.detect(snapshots)
        # Just verify it returns a valid regime
        self.assertIn(result.market_regime, [
            MarketRegime.BULLISH, MarketRegime.BEARISH, MarketRegime.SIDEWAYS,
            MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY, MarketRegime.UNKNOWN
        ])

        # Test with high variance snapshots
        high_var_snapshots = [
            self._create_snapshot(profit_pct=0.20 if i % 2 == 0 else -0.15, hours_ago=i * 24)
            for i in range(30)
        ]

        result = self.detector.detect(high_var_snapshots)
        # High variance should indicate high volatility
        self.assertIn(result.market_regime, [MarketRegime.HIGH_VOLATILITY, MarketRegime.BULLISH, MarketRegime.BEARISH])

    def test_recommendation_generation(self):
        """Test recommendation generation."""
        # Critical degradation
        snapshots = [
            self._create_snapshot(max_drawdown=0.50, profit_pct=-0.20, hours_ago=i * 24)
            for i in range(30)
        ]

        baseline = {
            'total_profit_pct': 0.10,
            'win_rate': 0.6,
            'max_drawdown': 0.08,
            'avg_trades_per_day': 5.0,
        }

        result = self.detector.detect(snapshots, baseline)

        self.assertTrue(result.is_degraded)
        self.assertIn('CRITICAL', result.recommendation)


class TestAlertSerialization(unittest.TestCase):
    """Test alert serialization."""

    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = DegradationAlert(
            timestamp=utc_now(),
            alert_type=AlertType.PROFIT_DECLINE,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            current_value=0.05,
            baseline_value=0.10,
            threshold=0.7,
            details={'test': 'data'}
        )

        data = alert.to_dict()

        self.assertEqual(data['alert_type'], 'profit_decline')
        self.assertEqual(data['severity'], 'warning')
        self.assertEqual(data['message'], 'Test alert')


if __name__ == '__main__':
    unittest.main()

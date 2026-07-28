"""Unit tests for deployment module."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from deployment.version_control import (
    StrategyVersionControl, StrategyVersion, VersionStatus
)
from deployment.strategy_deployer import (
    StrategyDeployer, DeploymentStatus, DeploymentConfig, DeploymentResult
)
from deployment.shadow_trader import (
    ShadowTrader, ShadowTradeResult, ShadowStatus, ShadowConfig
)
from deployment.rollback_manager import (
    RollbackManager, RollbackEvent, RollbackReason, RollbackConfig
)
from monitoring.performance_monitor import PerformanceMetrics


class TestStrategyVersionControl(unittest.TestCase):
    """Tests for StrategyVersionControl."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.versions_dir = os.path.join(self.temp_dir, "versions")
        self.vc = StrategyVersionControl(self.versions_dir)

        # Create a test strategy file
        self.strategy_file = os.path.join(self.temp_dir, "test_strategy.py")
        with open(self.strategy_file, 'w') as f:
            f.write("""
class TestStrategy:
    def __init__(self):
        pass

    def populate_indicators(self, dataframe):
        return dataframe
""")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_create_version(self):
        """Test creating a new version."""
        version = self.vc.create_version(
            strategy_name="TestStrategy",
            source_file=self.strategy_file,
            parameters={'param1': 10},
            backtest_metrics={'total_profit_pct': 0.15},
            notes="Initial version"
        )

        self.assertEqual(version.version_id, "v1")
        self.assertEqual(version.strategy_name, "TestStrategy")
        self.assertEqual(version.status, VersionStatus.CREATED)
        self.assertTrue(os.path.exists(version.file_path))

    def test_create_multiple_versions(self):
        """Test creating multiple versions."""
        v1 = self.vc.create_version(
            strategy_name="TestStrategy",
            source_file=self.strategy_file,
        )
        v2 = self.vc.create_version(
            strategy_name="TestStrategy",
            source_file=self.strategy_file,
            parent_version=v1.version_id
        )

        self.assertEqual(v1.version_id, "v1")
        self.assertEqual(v2.version_id, "v2")
        self.assertEqual(v2.parent_version, "v1")

    def test_get_version(self):
        """Test getting a specific version."""
        created = self.vc.create_version(
            strategy_name="TestStrategy",
            source_file=self.strategy_file,
        )

        retrieved = self.vc.get_version("TestStrategy", "v1")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.version_id, created.version_id)

    def test_get_all_versions(self):
        """Test getting all versions."""
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.create_version("TestStrategy", self.strategy_file)

        versions = self.vc.get_all_versions("TestStrategy")

        self.assertEqual(len(versions), 3)

    def test_update_status(self):
        """Test updating version status."""
        self.vc.create_version("TestStrategy", self.strategy_file)

        success = self.vc.update_status(
            "TestStrategy", "v1", VersionStatus.DEPLOYED
        )

        self.assertTrue(success)
        version = self.vc.get_version("TestStrategy", "v1")
        self.assertEqual(version.status, VersionStatus.DEPLOYED)

    def test_set_active(self):
        """Test setting a version as active."""
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.create_version("TestStrategy", self.strategy_file)

        # Set v1 as active
        self.vc.set_active("TestStrategy", "v1")
        v1 = self.vc.get_version("TestStrategy", "v1")
        self.assertEqual(v1.status, VersionStatus.ACTIVE)

        # Set v2 as active (should deactivate v1)
        self.vc.set_active("TestStrategy", "v2")
        v1 = self.vc.get_version("TestStrategy", "v1")
        v2 = self.vc.get_version("TestStrategy", "v2")

        self.assertEqual(v1.status, VersionStatus.DEPLOYED)
        self.assertEqual(v2.status, VersionStatus.ACTIVE)

    def test_get_active_version(self):
        """Test getting the active version."""
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v1")

        active = self.vc.get_active_version("TestStrategy")

        self.assertIsNotNone(active)
        self.assertEqual(active.version_id, "v1")

    def test_get_deployment_history(self):
        """Test getting deployment history."""
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v1")

        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v2")

        history = self.vc.get_deployment_history("TestStrategy")

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['version_id'], "v2")  # Most recent first

    def test_compare_versions(self):
        """Test comparing versions."""
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.10}
        )
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15}
        )

        comparison = self.vc.compare_versions("TestStrategy", "v1", "v2")

        self.assertIn('backtest_comparison', comparison)
        self.assertIn('total_profit_pct', comparison['backtest_comparison'])

    def test_list_strategies(self):
        """Test listing strategies."""
        self.vc.create_version("Strategy1", self.strategy_file)
        self.vc.create_version("Strategy2", self.strategy_file)

        strategies = self.vc.list_strategies()

        self.assertEqual(len(strategies), 2)
        self.assertIn("Strategy1", strategies)
        self.assertIn("Strategy2", strategies)


class TestStrategyDeployer(unittest.TestCase):
    """Tests for StrategyDeployer."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.versions_dir = os.path.join(self.temp_dir, "versions")
        self.target_dir = os.path.join(self.temp_dir, "target")
        self.backup_dir = os.path.join(self.temp_dir, "backup")

        os.makedirs(self.target_dir, exist_ok=True)

        self.vc = StrategyVersionControl(self.versions_dir)
        self.deployer = StrategyDeployer(
            self.vc,
            target_strategy_dir=self.target_dir,
            backup_dir=self.backup_dir
        )

        # Create test strategy
        self.strategy_file = os.path.join(self.temp_dir, "test_strategy.py")
        with open(self.strategy_file, 'w') as f:
            f.write("class TestStrategy: pass")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_validate_strategy(self):
        """Test strategy validation."""
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15, 'max_drawdown': 0.10}
        )

        is_valid, message = self.deployer.validate_strategy("TestStrategy", "v1")

        self.assertTrue(is_valid)

    def test_validate_strategy_no_backtest(self):
        """Test validation fails without backtest metrics."""
        self.vc.create_version("TestStrategy", self.strategy_file)

        is_valid, message = self.deployer.validate_strategy("TestStrategy", "v1")

        self.assertFalse(is_valid)
        self.assertIn("backtest", message.lower())

    def test_backup_current_strategy(self):
        """Test backing up current strategy."""
        # Create a strategy in target dir
        target_file = os.path.join(self.target_dir, "TestStrategy.py")
        with open(target_file, 'w') as f:
            f.write("class TestStrategy: pass")

        backup_path = self.deployer.backup_current_strategy("TestStrategy")

        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))

    def test_deploy(self):
        """Test full deployment."""
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15, 'max_drawdown': 0.10}
        )

        config = DeploymentConfig(require_approval=False)
        result = self.deployer.deploy("TestStrategy", "v1", config)

        self.assertEqual(result.status, DeploymentStatus.COMPLETED)

        # Check file was deployed
        deployed_file = os.path.join(self.target_dir, "TestStrategy.py")
        self.assertTrue(os.path.exists(deployed_file))

    def test_deploy_requires_approval_callback_by_default(self):
        """Test deployment fails closed when approval is required but unavailable."""
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15, 'max_drawdown': 0.10}
        )

        result = self.deployer.deploy("TestStrategy", "v1", DeploymentConfig())

        self.assertEqual(result.status, DeploymentStatus.FAILED)
        self.assertIn("approval callback", result.error_message.lower())
        deployed_file = os.path.join(self.target_dir, "TestStrategy.py")
        self.assertFalse(os.path.exists(deployed_file))

    def test_deploy_with_approval_callback(self):
        """Test deployment proceeds when approval callback allows it."""
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15, 'max_drawdown': 0.10}
        )
        self.deployer.set_approval_callback(lambda strategy, version: True)

        result = self.deployer.deploy("TestStrategy", "v1", DeploymentConfig())

        self.assertEqual(result.status, DeploymentStatus.COMPLETED)
        self.assertTrue(result.approved)
        self.assertTrue(any("not executed" in note for note in result.notes))

    def test_rollback(self):
        """Test rollback functionality."""
        # Create and deploy v1
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.15, 'max_drawdown': 0.10}
        )
        config = DeploymentConfig(require_approval=False)
        self.deployer.deploy("TestStrategy", "v1", config)

        # Create and deploy v2
        self.vc.create_version(
            "TestStrategy", self.strategy_file,
            backtest_metrics={'total_profit_pct': 0.20, 'max_drawdown': 0.08}
        )
        self.deployer.deploy("TestStrategy", "v2", config)

        # Rollback to v1
        success = self.deployer.rollback("TestStrategy", "v1")

        self.assertTrue(success)
        active = self.vc.get_active_version("TestStrategy")
        self.assertEqual(active.version_id, "v1")


class TestShadowTrader(unittest.TestCase):
    """Tests for ShadowTrader."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = os.path.join(self.temp_dir, "results")

        self.trader = ShadowTrader(
            freqtrade_path="/usr/local/bin/freqtrade",
            config_file="config.json",
            results_dir=self.results_dir
        )

        # Create test strategy
        self.strategy_file = os.path.join(self.temp_dir, "test_strategy.py")
        with open(self.strategy_file, 'w') as f:
            f.write("class TestStrategy: pass")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_start_shadow_trading(self):
        """Test starting shadow trading."""
        result = self.trader.start_shadow_trading(
            strategy_name="TestStrategy",
            version_id="v1",
            strategy_file=self.strategy_file
        )

        self.assertEqual(result.status, ShadowStatus.RUNNING)
        self.assertEqual(result.strategy_name, "TestStrategy")

    def test_simulate_shadow_session(self):
        """Test simulating shadow session from backtest."""
        backtest_metrics = {
            'total_trades': 50,
            'wins': 30,
            'losses': 20,
            'win_rate': 0.6,
            'profit_total': 500.0,
            'total_profit_pct': 0.10,
            'max_drawdown': 0.08,
            'profit_factor': 1.5,
        }

        result = self.trader.simulate_shadow_session(
            "TestStrategy", "v1", backtest_metrics
        )

        self.assertEqual(result.status, ShadowStatus.COMPLETED)
        self.assertEqual(result.total_trades, 50)
        self.assertEqual(result.win_rate, 0.6)

    def test_validate_results(self):
        """Test result validation."""
        result = ShadowTradeResult(
            session_id="test",
            strategy_name="TestStrategy",
            version_id="v1",
            status=ShadowStatus.COMPLETED,
            started_at=datetime.now(),
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            win_rate=0.6,
            total_profit_pct=0.05,
            max_drawdown=0.10,
        )

        config = ShadowConfig(
            min_trades_required=10,
            min_win_rate=0.4,
            max_drawdown=0.20
        )

        passed = self.trader.validate_results(result, config)

        self.assertTrue(passed)
        self.assertTrue(result.validation_passed)

    def test_validate_results_fail(self):
        """Test validation failure."""
        result = ShadowTradeResult(
            session_id="test",
            strategy_name="TestStrategy",
            version_id="v1",
            status=ShadowStatus.COMPLETED,
            started_at=datetime.now(),
            total_trades=3,  # Too few trades
            win_rate=0.3,    # Too low
            max_drawdown=0.30,  # Too high
        )

        config = ShadowConfig(
            min_trades_required=10,
            min_win_rate=0.4,
            max_drawdown=0.20
        )

        passed = self.trader.validate_results(result, config)

        self.assertFalse(passed)
        self.assertFalse(result.validation_passed)
        self.assertGreater(len(result.validation_notes), 0)

    def test_save_and_load_result(self):
        """Test saving and loading results."""
        result = ShadowTradeResult(
            session_id="shadow_TestStrategy_v1_20240101_120000",
            strategy_name="TestStrategy",
            version_id="v1",
            status=ShadowStatus.COMPLETED,
            started_at=datetime.now(),
            ended_at=datetime.now(),
            total_trades=20,
            win_rate=0.6,
        )

        # Save
        file_path = self.trader.save_result(result)
        self.assertTrue(os.path.exists(file_path))

        # Load
        loaded = self.trader.load_result(result.session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.strategy_name, "TestStrategy")


class TestRollbackManager(unittest.TestCase):
    """Tests for RollbackManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.versions_dir = os.path.join(self.temp_dir, "versions")
        self.history_file = os.path.join(self.temp_dir, "rollback_history.json")

        self.vc = StrategyVersionControl(self.versions_dir)
        self.manager = RollbackManager(
            self.vc,
            config=RollbackConfig(enabled=True, cooldown_minutes=0, require_confirmation=False),
            rollback_history_file=self.history_file
        )
        self.manager.set_deploy_callback(lambda strategy_name, version_id: True)

        # Create test strategy
        self.strategy_file = os.path.join(self.temp_dir, "test_strategy.py")
        with open(self.strategy_file, 'w') as f:
            f.write("class TestStrategy: pass")

        # Create versions
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v1")  # Deploy v1 first
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v2")  # Then deploy v2

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_check_triggers_drawdown(self):
        """Test drawdown trigger."""
        metrics = PerformanceMetrics()
        metrics.max_drawdown = 0.25  # Exceeds 0.15 threshold

        reason = self.manager._check_triggers(metrics)

        self.assertEqual(reason, RollbackReason.DRAWDOWN_EXCEEDED)

    def test_check_triggers_consecutive_losses(self):
        """Test consecutive losses trigger."""
        metrics = PerformanceMetrics()
        metrics.max_drawdown = 0.10
        metrics.max_consecutive_losses = 6  # Exceeds 5 threshold

        reason = self.manager._check_triggers(metrics)

        self.assertEqual(reason, RollbackReason.CONSECUTIVE_LOSSES)

    def test_check_triggers_no_trigger(self):
        """Test no trigger when metrics are good."""
        metrics = PerformanceMetrics()
        metrics.max_drawdown = 0.05
        metrics.max_consecutive_losses = 2
        metrics.win_rate = 0.6
        metrics.total_trades = 20

        reason = self.manager._check_triggers(metrics)

        self.assertIsNone(reason)

    def test_execute_rollback(self):
        """Test executing rollback."""
        event = self.manager.execute_rollback(
            "TestStrategy",
            RollbackReason.DRAWDOWN_EXCEEDED
        )

        self.assertIsNotNone(event)
        self.assertTrue(event.success)
        self.assertEqual(event.from_version, "v2")
        self.assertEqual(event.to_version, "v1")

        # Check version status
        v2 = self.vc.get_version("TestStrategy", "v2")
        self.assertEqual(v2.status, VersionStatus.ROLLED_BACK)

        active = self.vc.get_active_version("TestStrategy")
        self.assertEqual(active.version_id, "v1")

    def test_get_history(self):
        """Test getting rollback history."""
        self.manager.execute_rollback(
            "TestStrategy", RollbackReason.DRAWDOWN_EXCEEDED
        )

        history = self.manager.get_history("TestStrategy")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].reason, RollbackReason.DRAWDOWN_EXCEEDED)

    def test_cooldown(self):
        """Test cooldown period."""
        # Set cooldown to 60 minutes
        self.manager.config.cooldown_minutes = 60

        # First rollback - reset v2 as active first
        self.vc.set_active("TestStrategy", "v2")
        self.manager.execute_rollback("TestStrategy", RollbackReason.MANUAL)

        # Check cooldown is active
        self.assertTrue(self.manager.is_in_cooldown("TestStrategy"))

        remaining = self.manager.get_cooldown_remaining("TestStrategy")
        self.assertGreater(remaining, 0)

    def test_notify_callback(self):
        """Test notification callback."""
        notified = []

        def on_notify(event):
            notified.append(event)

        self.manager.set_notify_callback(on_notify)
        self.manager.execute_rollback("TestStrategy", RollbackReason.MANUAL)

        self.assertEqual(len(notified), 1)
        self.assertEqual(notified[0].strategy_name, "TestStrategy")

    def test_rollback_count(self):
        """Test rollback count."""
        # Execute a rollback
        self.manager.execute_rollback("TestStrategy", RollbackReason.MANUAL)

        count = self.manager.get_rollback_count("TestStrategy", hours=24)

        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()

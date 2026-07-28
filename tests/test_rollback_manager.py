"""Safety tests for rollback manager fail-closed behavior."""

import os
import shutil
import tempfile
import unittest

from deployment.rollback_manager import RollbackConfig, RollbackManager, RollbackReason
from deployment.version_control import StrategyVersionControl, VersionStatus
from monitoring.performance_monitor import PerformanceMetrics


class TestRollbackManagerSafety(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.versions_dir = os.path.join(self.temp_dir, "versions")
        self.history_file = os.path.join(self.temp_dir, "rollback_history.json")
        self.strategy_file = os.path.join(self.temp_dir, "strategy.py")
        with open(self.strategy_file, "w") as handle:
            handle.write("class TestStrategy: pass")

        self.vc = StrategyVersionControl(self.versions_dir)
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v1")
        self.vc.create_version("TestStrategy", self.strategy_file)
        self.vc.set_active("TestStrategy", "v2")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _manager(self, config):
        return RollbackManager(
            self.vc,
            config=config,
            rollback_history_file=self.history_file,
        )

    def test_auto_rollback_disabled_by_default(self):
        manager = self._manager(RollbackConfig())
        metrics = PerformanceMetrics()
        metrics.max_drawdown = 0.50

        event = manager.check_and_rollback("TestStrategy", metrics)

        self.assertIsNone(event)
        self.assertFalse(manager.config.enabled)
        self.assertEqual(self.vc.get_active_version("TestStrategy").version_id, "v2")

    def test_rollback_requires_confirmation_for_trading_strategy(self):
        manager = self._manager(RollbackConfig(enabled=True, cooldown_minutes=0))
        manager.set_deploy_callback(lambda strategy_name, version_id: True)

        event = manager.execute_rollback("TestStrategy", RollbackReason.DRAWDOWN_EXCEEDED)

        self.assertIsNone(event)
        self.assertEqual(self.vc.get_active_version("TestStrategy").version_id, "v2")

    def test_rollback_does_not_switch_active_version_without_deploy_callback(self):
        manager = self._manager(
            RollbackConfig(enabled=True, cooldown_minutes=0, require_confirmation=False)
        )

        event = manager.execute_rollback("TestStrategy", RollbackReason.DRAWDOWN_EXCEEDED)

        self.assertIsNotNone(event)
        self.assertFalse(event.success)
        self.assertIn("deploy_callback", event.notes)
        self.assertEqual(self.vc.get_active_version("TestStrategy").version_id, "v2")
        self.assertEqual(self.vc.get_version("TestStrategy", "v2").status, VersionStatus.ACTIVE)

    def test_rollback_fails_when_file_deployment_not_verified(self):
        manager = self._manager(
            RollbackConfig(enabled=True, cooldown_minutes=0, require_confirmation=False)
        )
        manager.set_deploy_callback(lambda strategy_name, version_id: False)

        event = manager.execute_rollback("TestStrategy", RollbackReason.DRAWDOWN_EXCEEDED)

        self.assertIsNotNone(event)
        self.assertFalse(event.success)
        self.assertEqual(self.vc.get_active_version("TestStrategy").version_id, "v2")
        self.assertEqual(self.vc.get_version("TestStrategy", "v2").status, VersionStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()

"""Tests for custom trading-system config adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.custom_strategy_schema import (
    CustomStrategyGenome,
    custom_strategy_config_from_genome,
)
from bollinger_evolver.trading_system_adapter import (
    build_position_sizing_preview,
    build_trading_system_config,
    write_trading_system_config,
)
from bollinger_evolver.fixtures.custom_strategy_fixtures import get_custom_strategy_fixture


def _strategy_config(**overrides):
    genome = CustomStrategyGenome(genome_id="adapter-safe-default", **overrides)
    return custom_strategy_config_from_genome(genome)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class TestTradingSystemAdapter(unittest.TestCase):
    def test_build_trading_system_config_maps_entry_parameters(self) -> None:
        config = build_trading_system_config(_strategy_config(entry_bb_window=34, entry_bb_stddev=2.4))

        self.assertEqual(config["entry"]["bollinger"]["window"], 34)
        self.assertEqual(config["entry"]["bollinger"]["stddev"], 2.4)
        self.assertEqual(config["entry"]["rsi"]["period"], 14)

    def test_build_trading_system_config_maps_exit_parameters(self) -> None:
        config = build_trading_system_config(
            _strategy_config(exit_stop_loss_pct=0.025, exit_take_profit_pct=0.075)
        )

        self.assertEqual(config["exit"]["stoploss_pct"], 0.025)
        self.assertEqual(config["exit"]["takeprofit_pct"], 0.075)
        self.assertLess(config["exit"]["stoploss_pct"], config["exit"]["takeprofit_pct"])

    def test_build_trading_system_config_maps_risk_parameters(self) -> None:
        config = build_trading_system_config(
            _strategy_config(leverage=2.5, risk_per_trade=0.015, max_additions=2)
        )

        self.assertEqual(config["position"]["base_leverage"], 2.5)
        self.assertEqual(config["position"]["max_leverage"], 2.5)
        self.assertEqual(config["position"]["risk_per_trade"], 0.015)
        self.assertEqual(config["position"]["max_open_positions"], 3)
        self.assertTrue(config["execution"]["dry_run_only"])
        self.assertFalse(config["execution"]["real_trading_enabled"])

    def test_build_trading_system_config_is_json_serializable(self) -> None:
        config = build_trading_system_config(_strategy_config())

        encoded = json.dumps(config, sort_keys=True)

        self.assertIn("custom-trading-system-config/v1", encoded)

    def test_build_trading_system_config_contains_no_secret_fields(self) -> None:
        strategy_config = _strategy_config()
        strategy_config["api_key"] = "redacted"

        with self.assertRaisesRegex(ValueError, "secret_field"):
            build_trading_system_config(strategy_config)

    def test_write_trading_system_config_to_tempdir(self) -> None:
        config = build_trading_system_config(_strategy_config())
        with tempfile.TemporaryDirectory() as tmp:
            path = write_trading_system_config(config, tmp)

            self.assertEqual(path.name, "trading_system_config.json")
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["strategy_id"], "adapter-safe-default")

    def test_write_trading_system_config_rejects_repo_root(self) -> None:
        config = build_trading_system_config(_strategy_config())

        with self.assertRaisesRegex(ValueError, "repo_root"):
            write_trading_system_config(config, _repo_root())

    def test_write_trading_system_config_rejects_runtime_dir(self) -> None:
        config = build_trading_system_config(_strategy_config())

        with self.assertRaisesRegex(ValueError, "disallowed"):
            write_trading_system_config(config, _repo_root() / ".runtime" / "adapter")

    def test_write_trading_system_config_rejects_workflow_dir(self) -> None:
        config = build_trading_system_config(_strategy_config())

        with self.assertRaisesRegex(ValueError, "disallowed"):
            write_trading_system_config(config, _repo_root() / ".workflow" / "adapter")

    def test_write_trading_system_config_rejects_user_data_data(self) -> None:
        config = build_trading_system_config(_strategy_config())

        with self.assertRaisesRegex(ValueError, "disallowed"):
            write_trading_system_config(config, _repo_root() / "user_data" / "data" / "config.json")

    def test_write_trading_system_config_rejects_strategy_dir(self) -> None:
        config = build_trading_system_config(_strategy_config())

        with self.assertRaisesRegex(ValueError, "disallowed"):
            write_trading_system_config(config, _repo_root() / "user_data" / "strategies" / "config.json")

    def test_position_sizing_preview_safe_default_calculates(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")
        config = build_trading_system_config(fixture["strategy_config"])

        preview = build_position_sizing_preview(config, equity=10_000.0)

        self.assertEqual(preview["schema_version"], "position-sizing/v1")
        self.assertGreater(preview["position_value"], 0)
        self.assertEqual(preview["source"], "trading-system-config")

    def test_position_sizing_preview_high_risk_fixture_warns(self) -> None:
        fixture = get_custom_strategy_fixture("high_leverage_high_drawdown")
        config = build_trading_system_config(fixture["strategy_config"])

        preview = build_position_sizing_preview(config, equity=10_000.0)

        self.assertIn("high_portfolio_exposure", preview["warnings"])
        self.assertIn("high_leverage_config", preview["warnings"])

    def test_position_sizing_preview_is_json_serializable(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")
        config = build_trading_system_config(fixture["strategy_config"])

        preview = build_position_sizing_preview(config, equity=10_000.0)

        encoded = json.dumps(preview, sort_keys=True)
        self.assertIn("position-sizing/v1", encoded)


if __name__ == "__main__":
    unittest.main()

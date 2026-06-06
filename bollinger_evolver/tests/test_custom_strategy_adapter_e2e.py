"""E2E mock flow tests for custom strategy config adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.fixtures.custom_strategy_fixtures import get_custom_strategy_fixture
from bollinger_evolver.ga_execution_custom import (
    CustomGAExecutionConfig,
    build_custom_ga_session_summary,
    evaluate_custom_genome,
    run_custom_ga_execution,
)
from bollinger_evolver.risk_governor import apply_risk_governor
from bollinger_evolver.trading_system_adapter import (
    build_trading_system_config,
    write_trading_system_config,
)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


class TestCustomStrategyAdapterE2E(unittest.TestCase):
    def test_custom_strategy_e2e_safe_default(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")

        trading_config = build_trading_system_config(fixture["strategy_config"])

        self.assertEqual(trading_config["strategy_id"], "fixture-safe-default")
        self.assertFalse(trading_config["execution"]["real_trading_enabled"])

    def test_custom_strategy_e2e_high_risk_gets_adjusted(self) -> None:
        fixture = get_custom_strategy_fixture("high_leverage_high_drawdown")

        advice = apply_risk_governor(fixture["strategy_config"], fixture["metrics"])

        self.assertLess(advice["adjusted_risk_per_trade"], fixture["genome"]["risk_per_trade"])
        self.assertIn("advisory_only_no_strategy_mutation", advice["explanation"])

    def test_custom_strategy_e2e_writes_config_only_to_tempdir(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")
        trading_config = build_trading_system_config(fixture["strategy_config"])
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp).resolve()
            path = write_trading_system_config(trading_config, temp_root)

            self.assertTrue(_is_relative_to(path.resolve(), temp_root))
            self.assertEqual(path.name, "trading_system_config.json")

    def test_custom_strategy_e2e_produces_session_summary(self) -> None:
        result = run_custom_ga_execution(
            CustomGAExecutionConfig(population_size=6, generations=2, seed=155, trade_count=30),
            run_id="custom-adapter-e2e",
        )
        summary = build_custom_ga_session_summary(result, top_n=3)

        self.assertEqual(summary["run_id"], "custom-adapter-e2e")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(len(summary["leaderboard"]), 3)

    def test_custom_strategy_e2e_produces_json_safe_artifact(self) -> None:
        fixture = get_custom_strategy_fixture("portfolio_balanced")
        evaluation = evaluate_custom_genome(CustomStrategyGenome(**fixture["genome"]))
        artifact = {
            "schema_version": "custom-adapter-e2e-evaluation/v1",
            "evaluation": evaluation.to_dict(),
        }

        encoded = json.dumps(artifact, sort_keys=True)

        self.assertIn("custom-adapter-e2e-evaluation/v1", encoded)
        self.assertFalse(evaluation.adjusted_strategy_config["execution_controls"]["real_execution_enabled"])

    def test_custom_strategy_e2e_artifact_payload_is_json_safe(self) -> None:
        fixture = get_custom_strategy_fixture("portfolio_balanced")
        result = run_custom_ga_execution(
            CustomGAExecutionConfig(population_size=6, generations=1, seed=160, trade_count=20),
            run_id="custom-adapter-artifact",
        )
        summary = build_custom_ga_session_summary(result, top_n=2)
        artifact = {
            "schema_version": "custom-adapter-e2e-artifact/v1",
            "fixture": fixture,
            "session_summary": summary,
            "safety": {
                "real_backtest_used": False,
                "freqtrade_used": False,
                "exchange_api_used": False,
            },
        }

        encoded = json.dumps(artifact, sort_keys=True)

        self.assertIn("custom-adapter-e2e-artifact/v1", encoded)
        self.assertFalse(artifact["safety"]["real_backtest_used"])


if __name__ == "__main__":
    unittest.main()

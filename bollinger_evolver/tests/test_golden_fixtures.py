"""Golden JSON fixture tests for stable mock-first contracts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.artifact_export import build_generation_artifact
from bollinger_evolver.backtest_adapter import MockBacktestAdapter
from bollinger_evolver.custom_strategy_schema import (
    CustomStrategyGenome,
    custom_strategy_config_from_genome,
)
from bollinger_evolver.experiment_registry import ExperimentRecord
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.monte_carlo import MonteCarloConfig, run_monte_carlo_stress_test
from bollinger_evolver.owner_review_pack import build_owner_review_pack
from bollinger_evolver.preflight import build_offline_data_preflight_report
from bollinger_evolver.risk_budget import RiskBudgetConfig, simulate_risk_budget
from bollinger_evolver.risk_cli import build_fixture_risk_report
from bollinger_evolver.session_summary import build_ga_session_summary
from bollinger_evolver.walk_forward_custom import CustomWalkForwardConfig, evaluate_custom_walk_forward


GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
FIXTURE_FILES = (
    "offline_preflight_sample.json",
    "custom_strategy_config_sample.json",
    "mock_ga_session_summary_sample.json",
    "generation_artifact_sample.json",
    "normalized_backtest_result_sample.json",
    "experiment_registry_record_sample.json",
    "risk_report_sample.json",
    "owner_review_pack_sample.json",
)
RISK_SCENARIO_FIXTURE_FILES = (
    "safe_default.json",
    "high_leverage.json",
    "high_drawdown.json",
    "loss_streak.json",
    "portfolio_exposure_breach.json",
    "monte_carlo_failure.json",
    "walk_forward_overfit.json",
)


def _load_fixture(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def _assert_json_safe(testcase: unittest.TestCase, payload: dict) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    testcase.assertIsInstance(json.loads(encoded), dict)


class TestGoldenFixtures(unittest.TestCase):
    def test_golden_fixtures_can_load(self) -> None:
        for name in (*FIXTURE_FILES, *RISK_SCENARIO_FIXTURE_FILES):
            with self.subTest(name=name):
                payload = _load_fixture(name)
                self.assertIsInstance(payload, dict)
                self.assertIn("schema_version", payload)

    def test_golden_fixtures_are_json_safe(self) -> None:
        for name in (*FIXTURE_FILES, *RISK_SCENARIO_FIXTURE_FILES):
            with self.subTest(name=name):
                _assert_json_safe(self, _load_fixture(name))

    def test_custom_strategy_risk_scenarios_are_adapter_consumable(self) -> None:
        for name in ("safe_default.json", "high_leverage.json", "high_drawdown.json", "loss_streak.json"):
            with self.subTest(name=name):
                payload = _load_fixture(name)
                genome = CustomStrategyGenome(**payload["genome"])
                generated = custom_strategy_config_from_genome(genome)

                self.assertEqual(generated["schema_version"], "custom-strategy/v1")
                self.assertEqual(generated["genome_id"], payload["genome"]["genome_id"])

    def test_portfolio_exposure_breach_fixture_feeds_risk_budget(self) -> None:
        payload = _load_fixture("portfolio_exposure_breach.json")

        result = simulate_risk_budget(
            payload["positions"],
            config=RiskBudgetConfig(**payload["limits"]),
        )
        violation_codes = {item["code"] for item in result["violations"]}

        self.assertFalse(result["ok"])
        self.assertTrue(set(payload["expected_violation_codes"]).issubset(violation_codes))

    def test_monte_carlo_failure_fixture_feeds_stress_test(self) -> None:
        payload = _load_fixture("monte_carlo_failure.json")

        result = run_monte_carlo_stress_test(payload["trades"], config=MonteCarloConfig(**payload["config"]))

        self.assertEqual(result["schema_version"], "monte-carlo-stress/v1")
        self.assertGreaterEqual(result["failure_rate"], payload["expected"]["failure_rate_min"])

    def test_walk_forward_overfit_fixture_feeds_custom_adapter(self) -> None:
        payload = _load_fixture("walk_forward_overfit.json")
        genome = CustomStrategyGenome(**payload["genome"])

        result = evaluate_custom_walk_forward(genome, config=CustomWalkForwardConfig(**payload["config"]))

        self.assertEqual(result["schema_version"], payload["expected"]["schema_version"])
        self.assertIn("walk_forward", result)
        self.assertIn("fitness_components", result)

    def test_offline_preflight_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("offline_preflight_sample.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            generated = build_offline_data_preflight_report(root).to_dict()

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertIn("summary", generated)
        self.assertIn("datasets", generated)

    def test_custom_strategy_config_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("custom_strategy_config_sample.json")

        generated = custom_strategy_config_from_genome(CustomStrategyGenome(genome_id="golden-custom-001"))

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertIn("entry", generated)
        self.assertIn("position_sizing", generated)

    def test_mock_ga_session_summary_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("mock_ga_session_summary_sample.json")
        result = run_ga_execution(GAExecutionConfig(population_size=4, generations=1, seed=2026))

        generated = build_ga_session_summary(result, top_n=1, run_id="golden-ga-session")

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertIn("leaderboard", generated)
        self.assertIn("fitness_series", generated)

    def test_generation_artifact_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("generation_artifact_sample.json")
        result = run_ga_execution(GAExecutionConfig(population_size=4, generations=1, seed=77))

        generated = build_generation_artifact(result, top_n=1, run_id="golden-ga-session")

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertIn("session_summary", generated)
        self.assertIn("genomes", generated)

    def test_normalized_backtest_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("normalized_backtest_result_sample.json")
        result = MockBacktestAdapter(seed=2026, trade_count=20).run_backtest(
            {
                "genome_id": "golden-normalized",
                "bb_period": 20,
                "bb_stddev": 2.0,
                "stop_loss": 0.03,
                "take_profit": 0.08,
                "leverage": 1.0,
                "risk_per_trade": 0.01,
            }
        )
        generated = {"schema_version": result.metadata["schema_version"], **result.to_dict()}

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertEqual(generated["metadata"]["schema_version"], fixture["schema_version"])

    def test_experiment_registry_record_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("experiment_registry_record_sample.json")
        record = ExperimentRecord(
            run_id="golden-run",
            source="mock-ga-cli",
            seed=2026,
            generations=1,
            population_size=4,
            best_fitness=0.24,
            artifact_dir="artifacts/golden-run",
            notes="golden fixture",
            created_at="2026-06-06T00:00:00+00:00",
        )
        generated = {"schema_version": fixture["schema_version"], **record.to_dict()}

        self.assertTrue(set(fixture).issubset(generated))
        self.assertEqual(generated["schema_version"], "experiment-registry-record/v1")

    def test_risk_report_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("risk_report_sample.json")

        generated, _ = build_fixture_risk_report("safe_default")

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertEqual(generated["safety"]["real_backtest_used"], False)

    def test_owner_review_pack_generated_fields_cover_fixture(self) -> None:
        fixture = _load_fixture("owner_review_pack_sample.json")

        generated = build_owner_review_pack()

        self.assertEqual(generated["schema_version"], fixture["schema_version"])
        self.assertTrue(set(fixture).issubset(generated))
        self.assertEqual(generated["real_backtest_gate"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

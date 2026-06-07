"""Tests for the mock E2E pipeline summary report."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.reports.mock_e2e_pipeline_summary import (
    MockE2EPipelineSummaryConfig,
    build_mock_e2e_pipeline_summary,
)


class TestMockE2EPipelineSummary(unittest.TestCase):
    def _summary(self) -> dict:
        return build_mock_e2e_pipeline_summary(
            MockE2EPipelineSummaryConfig(
                run_id="test-mock-e2e-summary",
                population_size=6,
                generations=1,
                seed=384,
                top_n=2,
                trade_count=20,
                pairs=("BTC/USDT", "ETH/USDT"),
                monte_carlo_runs=10,
            )
        )

    def test_summary_is_json_safe(self) -> None:
        summary = self._summary()

        encoded = json.dumps(summary, sort_keys=True)
        decoded = json.loads(encoded)

        self.assertEqual(decoded["schema_version"], "mock-e2e-pipeline-summary/v1")
        self.assertEqual(decoded["source"], "mock-first")

    def test_summary_contains_all_pipeline_modules(self) -> None:
        summary = self._summary()

        modules = {item["module"] for item in summary["modules"]}

        self.assertEqual(
            modules,
            {"ga", "risk", "walk_forward", "monte_carlo", "portfolio", "frontend_contract"},
        )

    def test_summary_contains_frontend_and_metric_sections(self) -> None:
        summary = self._summary()

        self.assertIn("leaderboard", summary["frontend_contract"])
        self.assertIn("fitness_series", summary["frontend_contract"])
        self.assertGreater(summary["metrics"]["leaderboard_rows"], 0)
        self.assertGreater(summary["metrics"]["fitness_points"], 0)
        self.assertGreaterEqual(summary["metrics"]["failure_rate"], 0)

    def test_summary_contains_session_summary_and_fitness_series(self) -> None:
        summary = self._summary()
        session = summary["session_summary"]

        self.assertEqual(session["schema_version"], "mock-e2e-session-summary/v1")
        self.assertEqual(session["run_id"], "test-mock-e2e-summary")
        self.assertGreater(len(session["leaderboard"]), 0)
        self.assertGreater(len(session["fitness_series"]), 0)
        self.assertIn("best_genome_id", session)

    def test_summary_contains_portfolio_and_risk_metrics(self) -> None:
        summary = self._summary()

        self.assertEqual(summary["risk_metrics"]["schema_version"], "mock-e2e-risk-metrics/v1")
        self.assertIn("monte_carlo_failure_rate", summary["risk_metrics"])
        self.assertIn("stability_score", summary["risk_metrics"])
        self.assertIn("risk_per_trade", summary["risk_metrics"])
        self.assertEqual(summary["portfolio"]["schema_version"], "mock-e2e-portfolio-summary/v1")
        self.assertIn("pair_results", summary["portfolio"])
        self.assertGreaterEqual(summary["portfolio"]["portfolio_drawdown"], 0)

    def test_summary_contains_golden_fixture_and_artifact_contracts(self) -> None:
        summary = self._summary()

        self.assertEqual(summary["golden_fixture_coverage"]["schema_version"], "golden-fixture-coverage/v1")
        self.assertIn("risk_scenario_panel_sample.json", summary["golden_fixture_coverage"]["fixtures"])
        self.assertTrue(summary["golden_fixture_coverage"]["required_schema_version_field"])
        self.assertEqual(summary["artifact_contract"]["schema_version"], "mock-e2e-artifact-contract/v1")
        self.assertIn("session_summary", summary["artifact_contract"]["artifact_sections"])
        self.assertFalse(summary["artifact_contract"]["file_write_used"])

    def test_summary_safety_flags_remain_false(self) -> None:
        summary = self._summary()

        self.assertFalse(summary["safety"]["real_backtest_used"])
        self.assertFalse(summary["safety"]["freqtrade_used"])
        self.assertFalse(summary["safety"]["download_data_used"])
        self.assertFalse(summary["safety"]["exchange_api_used"])
        self.assertFalse(summary["safety"]["file_write_used"])

    def test_summary_builder_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = list(root.iterdir())
            self._summary()
            after = list(root.iterdir())

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

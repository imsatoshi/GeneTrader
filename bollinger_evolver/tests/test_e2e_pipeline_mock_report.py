"""Tests for the mock-first E2E pipeline report builder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.reports.e2e_pipeline_mock_report import (
    E2EMockPipelineReportConfig,
    build_e2e_mock_pipeline_report,
)


class TestE2EMockPipelineReport(unittest.TestCase):
    def _report(self) -> dict:
        return build_e2e_mock_pipeline_report(
            E2EMockPipelineReportConfig(
                run_id="test-e2e-report",
                population_size=6,
                generations=1,
                seed=325,
                top_n=2,
                trade_count=20,
                pairs=("BTC/USDT", "ETH/USDT"),
                monte_carlo_runs=10,
            )
        )

    def test_e2e_report_is_json_safe(self) -> None:
        report = self._report()

        encoded = json.dumps(report, sort_keys=True)
        self.assertIn("e2e-mock-pipeline-report/v1", encoded)
        self.assertEqual(json.loads(encoded)["source"], "mock-first")

    def test_e2e_report_contains_all_sections(self) -> None:
        report = self._report()

        self.assertEqual(
            set(report["sections"]),
            {"ga", "risk", "walk_forward", "monte_carlo", "portfolio", "frontend_contract"},
        )

    def test_e2e_report_safety_flags_remain_false(self) -> None:
        report = self._report()

        self.assertFalse(report["safety"]["real_backtest_used"])
        self.assertFalse(report["safety"]["exchange_api_used"])
        self.assertFalse(report["safety"]["freqtrade_used"])
        self.assertFalse(report["safety"]["download_data_used"])

    def test_e2e_report_frontend_contract_summary_is_present(self) -> None:
        report = self._report()
        frontend_contract = report["sections"]["frontend_contract"]

        self.assertEqual(frontend_contract["schema_version"], "frontend-contract-summary/v1")
        self.assertGreater(frontend_contract["leaderboard_rows"], 0)
        self.assertGreater(frontend_contract["fitness_points"], 0)
        self.assertTrue(frontend_contract["has_monte_carlo"])
        self.assertTrue(frontend_contract["has_portfolio"])

    def test_e2e_report_builder_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = list(root.iterdir())
            self._report()
            after = list(root.iterdir())

        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

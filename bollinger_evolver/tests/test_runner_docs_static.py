"""Static safety checks for the Bollinger Evolver runner runbook."""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = PROJECT_ROOT / "docs" / "bollinger_evolver_runner_runbook.md"
TEST_BASELINE_PATH = PROJECT_ROOT / "docs" / "test_baseline.md"
README_PATH = PROJECT_ROOT / "README.md"
RUNNER_CLI_TEST_PATH = PROJECT_ROOT / "bollinger_evolver" / "tests" / "test_ga_runner_cli.py"


class TestRunnerDocsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
        cls.test_baseline = TEST_BASELINE_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.runner_cli_tests = RUNNER_CLI_TEST_PATH.read_text(encoding="utf-8")

    def test_runbook_exists(self) -> None:
        self.assertTrue(RUNBOOK_PATH.exists())

    def test_runbook_includes_safety_positioning(self) -> None:
        required_tokens = [
            "mock-first",
            "real_backtest=false",
            "allow_real_backtest=False",
            "no exchange connection",
            "no API key / secret",
            "no live trading",
            "no Freqtrade backtest/hyperopt by default",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.runbook)

    def test_runbook_includes_artifacts_and_review_fields(self) -> None:
        required_tokens = [
            "session_summary.json",
            "session_report.json",
            "session_report.md",
            "dataQualityGate",
            "generation_summaries",
            "final_best",
            "riskAndSafety",
            "recommendation",
            "mock_evaluation=true",
            "real_backtest=false",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.runbook)

    def test_runbook_warns_about_disable_gate_and_forbidden_flags(self) -> None:
        required_tokens = [
            "--disable-data-quality-gate",
            "--allow-real-backtest",
            "--live",
            "--api-key",
            "--secret",
            "exchange/live args",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.runbook)

    def test_readme_or_test_baseline_links_to_runbook(self) -> None:
        token = "docs/bollinger_evolver_runner_runbook.md"
        self.assertTrue(token in self.test_baseline or token in self.readme)

    def test_runner_cli_tests_still_reject_live_or_secret_args(self) -> None:
        required_tokens = [
            "test_rejects_allow_real_backtest_argument",
            "test_rejects_live_argument",
            "test_rejects_secret_arguments",
            "unsupported_live_or_secret_argument",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.runner_cli_tests)


if __name__ == "__main__":
    unittest.main()

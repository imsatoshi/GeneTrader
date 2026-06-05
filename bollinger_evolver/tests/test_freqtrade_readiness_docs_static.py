"""Static checks for the Freqtrade readiness planning document."""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "freqtrade_environment_readiness_plan.md"


class TestFreqtradeReadinessDocsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc_text = DOC_PATH.read_text(encoding="utf-8")

    def test_document_exists(self) -> None:
        self.assertTrue(DOC_PATH.exists())

    def test_contains_current_warn_verdict(self) -> None:
        required_tokens = [
            "status=WARN",
            "freqtrade_available=false",
            "strategy_import_ok=false",
            "data manifest missing",
            "safety boundaries PASS",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_environment_isolation_guidance(self) -> None:
        required_tokens = [
            "dedicated virtual environment",
            "conda environment",
            "Do not install Freqtrade into the base Python",
            "bollinger-ft-readiness",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_no_api_keys_or_live_trading_guidance(self) -> None:
        required_tokens = [
            "No API keys.",
            "No live trading.",
            "exchange connection",
            "secret injection",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_nonexecuting_setup_commands(self) -> None:
        required_tokens = [
            "python -m venv .venv-freqtrade",
            ".venv-freqtrade\\Scripts\\Activate.ps1",
            "python -m pip install freqtrade",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_manifest_requirements_and_path_to_ready(self) -> None:
        required_tokens = [
            "## Data Manifest Requirements",
            "minimum candle count",
            "gap ratio",
            "invalid OHLC count is `0`",
            "## Path to READY",
            "Install Freqtrade in an isolated environment.",
            "Provide a valid data manifest and pass the data quality gate.",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_allow_real_backtest_false_boundary(self) -> None:
        self.assertIn("allow_real_backtest=False", self.doc_text)

    def test_keeps_backtesting_and_hyperopt_forbidden(self) -> None:
        required_tokens = [
            "Freqtrade backtesting",
            "Freqtrade hyperopt",
            "still mock-first and read-only",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)


if __name__ == "__main__":
    unittest.main()

"""Static checks for the offline data acquisition planning document."""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "offline_data_acquisition_plan.md"


class TestOfflineDataPlanDocsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc_text = DOC_PATH.read_text(encoding="utf-8")

    def test_document_exists(self) -> None:
        self.assertTrue(DOC_PATH.exists())

    def test_contains_current_fail_verdict(self) -> None:
        required_tokens = [
            "status=FAIL",
            "allowed_for_evaluation=false",
            'required_pairs=["BTC/USDT"]',
            'required_timeframes=["15m","1h","4h"]',
            "missing_pair_timeframes",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_required_pair_timeframes(self) -> None:
        required_tokens = [
            "BTC/USDT",
            "15m",
            "1h",
            "4h",
            "BTC/USDT 15m",
            "BTC/USDT 1h",
            "BTC/USDT 4h",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_minimum_and_recommended_candles(self) -> None:
        required_tokens = [
            "minimum candles per pair/timeframe: `100`",
            "`15m`: `>= 5000`",
            "`1h`: `>= 2000`",
            "`4h`: `>= 1000`",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_required_fields(self) -> None:
        required_tokens = [
            "`timestamp` or `date`",
            "`open`",
            "`high`",
            "`low`",
            "`close`",
            "`volume`",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_accepted_formats(self) -> None:
        required_tokens = [
            ".json",
            ".jsonl",
            ".csv",
            ".feather",
            ".parquet",
            "CSV example",
            "JSON list example",
            "JSON dict list example",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_manifest_and_gate_commands(self) -> None:
        required_tokens = [
            "build_offline_data_manifest",
            "evaluate_data_coverage_gate",
            "required_pairs=['BTC/USDT']",
            "required_timeframes=['15m','1h','4h']",
            "min_candles_per_pair_timeframe=100",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_data_quality_requirements(self) -> None:
        required_tokens = [
            "duplicate timestamps: `0`",
            "out-of-order rows: `0`",
            "invalid OHLC: `0` required",
            "missing OHLC: `0` required",
            "gap ratio: `<= 0.02`",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_contains_path_from_fail_to_ready(self) -> None:
        required_tokens = [
            "## Path From FAIL to READY",
            "Prepare local `BTC/USDT` files",
            "Run the offline manifest builder.",
            "Confirm `allowed_for_evaluation=true`.",
            "Re-run backtest preflight with the generated `data_manifest_path`.",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)

    def test_keeps_forbidden_boundaries(self) -> None:
        required_tokens = [
            "downloading data",
            "connecting to an exchange",
            "using API keys",
            "writing secrets",
            "running `freqtrade download-data`",
            "running Freqtrade backtesting",
            "running Freqtrade hyperopt",
            "live trading",
        ]
        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, self.doc_text)


if __name__ == "__main__":
    unittest.main()

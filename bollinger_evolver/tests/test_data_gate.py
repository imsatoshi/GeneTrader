"""Tests for the read-only offline data manifest gate."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import bollinger_evolver.data_gate as data_gate
from bollinger_evolver.data_gate import run_offline_data_gate


def _rows(count: int = 120, step_ms: int = 900_000) -> list[list[object]]:
    base = 1714521600000
    return [
        [base + (index * step_ms), 100.0, 105.0, 99.0, 102.0, 10.0]
        for index in range(count)
    ]


class TestOfflineDataGate(unittest.TestCase):
    def _write_json(self, root: Path, timeframe: str, rows: list[object] | None = None) -> None:
        (root / f"BTC_USDT-{timeframe}.json").write_text(
            json.dumps(rows if rows is not None else _rows()),
            encoding="utf-8",
        )

    def _write_csv(
        self,
        root: Path,
        timeframe: str,
        rows: list[dict[str, object]] | None = None,
        fieldnames: list[str] | None = None,
    ) -> None:
        fields = fieldnames or ["timestamp", "open", "high", "low", "close", "volume"]
        with (root / f"BTC_USDT-{timeframe}.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            if rows is not None:
                writer.writerows(rows)

    def test_no_data_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_dir = Path(temp_dir) / "missing"
            result = run_offline_data_gate(data_dir=missing_dir)

        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertIn("data_dir_not_found", result["blocked_reasons"])

    def test_empty_data_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertEqual(sorted(result["missing_timeframes"]), ["15m", "1h", "4h"])

    def test_only_15m_exists_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_json(root, "15m")
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertEqual(sorted(result["missing_timeframes"]), ["1h", "4h"])

    def test_15m_and_1h_exists_but_4h_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_json(root, "15m")
            self._write_json(root, "1h", _rows(step_ms=3_600_000))
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertEqual(result["missing_timeframes"], ["4h"])

    def test_unsupported_required_file_format_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-15m.txt").write_text("not accepted", encoding="utf-8")
            result = run_offline_data_gate(data_dir=temp_dir, required_timeframes=["15m"])

        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertIn("unsupported_format", result["blocked_reasons"])

    def test_all_files_exist_but_empty_is_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for timeframe in ("15m", "1h", "4h"):
                (root / f"BTC_USDT-{timeframe}.json").write_text("[]", encoding="utf-8")
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertIn("empty_file", result["blocked_reasons"])

    def test_all_files_exist_but_missing_ohlcv_columns_is_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incomplete_rows = [{"timestamp": 1714521600000, "open": 100}]
            for timeframe in ("15m", "1h", "4h"):
                self._write_json(root, timeframe, incomplete_rows)
            result = run_offline_data_gate(data_dir=temp_dir, min_candles_per_pair_timeframe=1)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["allowed_for_evaluation"])
        self.assertIn("missing_ohlcv_columns", result["blocked_reasons"])

    def test_all_required_files_valid_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_json(root, "15m")
            self._write_json(root, "1h", _rows(step_ms=3_600_000))
            self._write_json(root, "4h", _rows(step_ms=14_400_000))
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["allowed_for_evaluation"])
        self.assertEqual(result["safe_next_action"], "ready_for_preflight")

    def test_ready_payload_contains_manifest_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_json(root, "15m")
            self._write_json(root, "1h", _rows(step_ms=3_600_000))
            self._write_json(root, "4h", _rows(step_ms=14_400_000))
            result = run_offline_data_gate(data_dir=temp_dir)

        self.assertEqual(result["schema_version"], "offline_data_manifest.v1")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["required_timeframes"], ["15m", "1h", "4h"])
        self.assertTrue(result["format_checks"]["accepted_format"])
        self.assertTrue(result["quality_checks"]["has_timestamp_column"])
        self.assertTrue(result["quality_checks"]["has_ohlcv_columns"])

    def test_fail_and_partial_never_allow_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fail_result = run_offline_data_gate(data_dir=temp_dir)
            root = Path(temp_dir)
            for timeframe in ("15m", "1h", "4h"):
                (root / f"BTC_USDT-{timeframe}.json").write_text("[]", encoding="utf-8")
            partial_result = run_offline_data_gate(data_dir=temp_dir)

        self.assertFalse(fail_result["allowed_for_evaluation"])
        self.assertFalse(partial_result["allowed_for_evaluation"])

    def test_gate_module_does_not_import_downloader_exchange_or_backtest_modules(self) -> None:
        module_file = Path(data_gate.__file__).read_text(encoding="utf-8")
        forbidden_tokens = [
            "data.downloader",
            "freqtrade",
            "ccxt",
            "backtesting",
            "hyperopt",
            "strategy.backtest",
        ]
        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, module_file)

    def test_cli_outputs_json_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bollinger_evolver.data_gate",
                    "--data-dir",
                    temp_dir,
                    "--symbol",
                    "BTC/USDT",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "FAIL")
        self.assertFalse(payload["allowed_for_evaluation"])
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()

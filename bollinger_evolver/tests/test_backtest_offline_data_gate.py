"""Tests for metadata-only backtest offline data gate adapter."""

from __future__ import annotations

import builtins
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_backtest_gate import (
    build_backtest_offline_data_gate,
    run_backtest_offline_data_gate,
)
from bollinger_evolver.offline_preflight_cli import EXIT_OK, EXIT_PREFLIGHT_FAILED


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestBacktestOfflineDataGate(unittest.TestCase):
    def _write(self, root: Path, name: str, content: str = PAYLOAD) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_gate_passes_for_fake_temp_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            result = run_backtest_offline_data_gate(root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertFalse(result["metadata"]["real_backtest_executed"])

    def test_gate_fails_for_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_backtest_offline_data_gate(Path(temp_dir))

        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], EXIT_PREFLIGHT_FAILED)
        self.assertTrue(result["issues"])

    def test_gate_fails_for_missing_required_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            result = run_backtest_offline_data_gate(root, required_suffixes=["json"])

        self.assertFalse(result["ok"])
        self.assertIn("required_suffix_missing", [item["code"] for item in result["issues"]])

    def test_gate_fails_when_max_total_size_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", "abcdef")
            result = run_backtest_offline_data_gate(root, max_total_size_bytes=3)

        self.assertFalse(result["ok"])
        self.assertIn("max_total_size_bytes_exceeded", [item["code"] for item in result["issues"]])

    def test_gate_fail_on_warning_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            self._write(root, "README.txt")
            result = run_backtest_offline_data_gate(root, fail_on_warning=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], EXIT_PREFLIGHT_FAILED)
        self.assertTrue(result["warnings"])

    def test_gate_output_is_deterministic_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            first = build_backtest_offline_data_gate(root, required_suffixes=["json", "csv"])
            second = build_backtest_offline_data_gate(root, required_suffixes=["json", "csv"])

        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_gate_payload_guard_and_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_file = self._write(root, "BTC_USDT-1h.csv").resolve()
            original_read_text = Path.read_text
            original_read_bytes = Path.read_bytes
            original_open = builtins.open

            def guarded_read_text(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_text(path, *args, **kwargs)

            def guarded_read_bytes(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_bytes(path, *args, **kwargs)

            def guarded_open(file, mode="r", *args, **kwargs):
                if "r" in mode:
                    try:
                        if Path(file).resolve() == fake_file:
                            raise AssertionError("fake market content read")
                    except TypeError:
                        pass
                return original_open(file, mode, *args, **kwargs)

            with patch.object(Path, "read_text", guarded_read_text):
                with patch.object(Path, "read_bytes", guarded_read_bytes):
                    with patch.object(builtins, "open", guarded_open):
                        result = run_backtest_offline_data_gate(root)

        self.assertTrue(result["ok"])
        self.assertNotIn(PAYLOAD, json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    unittest.main()

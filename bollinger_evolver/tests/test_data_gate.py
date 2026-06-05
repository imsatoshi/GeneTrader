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
from bollinger_evolver.data_gate import run_inventory_manifest_gate, run_offline_data_gate
from bollinger_evolver.data_manifest import build_manifest_from_inventory
from bollinger_evolver.offline_data import inventory_offline_data


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
                    "-W",
                    "ignore::RuntimeWarning",
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


class TestInventoryManifestGate(unittest.TestCase):
    def _write(self, root: Path, name: str, content: bytes = b"x") -> None:
        (root / name).write_bytes(content)

    def _manifest_for_root(self, root: Path) -> dict[str, object]:
        return build_manifest_from_inventory(inventory_offline_data(root))

    def test_gate_accepts_valid_inventory_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            result = run_inventory_manifest_gate(self._manifest_for_root(root))

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_gate_rejects_empty_inventory_manifest(self) -> None:
        result = run_inventory_manifest_gate({"root": "C:/tmp/offline", "datasets": []})

        self.assertFalse(result["ok"])
        self.assertIn("datasets_empty", result["errors"])

    def test_gate_rejects_missing_dataset_file_when_root_is_provided(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = {
                "root": temp_dir,
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
            result = run_inventory_manifest_gate(manifest)

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].file_missing", result["errors"])

    def test_gate_rejects_empty_dataset_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json", b"")
            result = run_inventory_manifest_gate(self._manifest_for_root(root))

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].file_empty", result["errors"])

    def test_gate_rejects_absolute_dataset_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file_path = root / "BTC_USDT-1h.json"
            self._write(root, "BTC_USDT-1h.json")
            manifest = {
                "root": temp_dir,
                "datasets": [
                    {
                        "path": str(file_path),
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
            result = run_inventory_manifest_gate(manifest)

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].dataset_path_unsafe", result["errors"])

    def test_gate_rejects_parent_directory_escape(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "root": "C:/tmp/offline",
                "datasets": [
                    {
                        "path": "../BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].dataset_path_unsafe", result["errors"])

    def test_gate_rejects_nested_parent_escape(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "root": "C:/tmp/offline",
                "datasets": [
                    {
                        "path": "nested/../../BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].dataset_path_unsafe", result["errors"])

    def test_gate_rejects_windows_drive_path(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "root": "C:/tmp/offline",
                "datasets": [
                    {
                        "path": "C:/tmp/offline/BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].dataset_path_unsafe", result["errors"])

    def test_gate_accepts_safe_relative_nested_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested_file = root / "nested" / "BTC_USDT-1h.json"
            nested_file.parent.mkdir()
            nested_file.write_bytes(b"x")
            manifest = {
                "root": temp_dir,
                "datasets": [
                    {
                        "path": "nested/BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
            result = run_inventory_manifest_gate(manifest)

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_gate_rejects_unsupported_format(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.txt",
                        "format": "txt",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].format_unsupported", result["errors"])

    def test_gate_rejects_invalid_pair(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC-USDT",
                        "timeframe": "1h",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].pair_invalid", result["errors"])

    def test_gate_rejects_invalid_timeframe(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-fast.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "fast",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].timeframe_invalid", result["errors"])

    def test_gate_reports_multiple_errors(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": str(Path("C:/absolute/BTC_USDT-fast.txt")),
                        "format": "txt",
                        "size_bytes": 0,
                        "pair": "BTC-USDT",
                        "timeframe": "fast",
                    }
                ],
            }
        )

        self.assertFalse(result["ok"])
        self.assertGreaterEqual(len(result["errors"]), 4)

    def test_gate_ignores_missing_probe_by_default(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ]
            }
        )

        self.assertTrue(result["ok"])

    def test_gate_fails_when_probe_reports_missing_ohlcv_columns(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.csv",
                        "format": "csv",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "probe": {"has_ohlcv_columns": False, "row_count_estimate": 120},
                    }
                ]
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].probe_missing_ohlcv_columns", result["errors"])

    def test_gate_passes_when_probe_reports_ohlcv_columns_present(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.csv",
                        "format": "csv",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "probe": {"has_ohlcv_columns": True, "row_count_estimate": 120},
                    }
                ]
            }
        )

        self.assertTrue(result["ok"])

    def test_min_candles_passes_when_rows_estimated_enough(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.csv",
                        "format": "csv",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "probe": {"has_ohlcv_columns": True, "row_count_estimate": 120},
                    }
                ]
            },
            min_candles_per_dataset=100,
        )

        self.assertTrue(result["ok"])

    def test_min_candles_fails_when_rows_estimated_too_low(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.csv",
                        "format": "csv",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "probe": {"has_ohlcv_columns": True, "row_count_estimate": 10},
                    }
                ]
            },
            min_candles_per_dataset=100,
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].row_count_below_minimum", result["errors"])

    def test_min_candles_warns_when_row_count_unknown(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.csv",
                        "format": "csv",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ]
            },
            min_candles_per_dataset=100,
        )

        self.assertTrue(result["ok"])
        self.assertIn("datasets[0].row_count_unknown", result["warnings"])

    def test_gate_accepts_valid_dataset_date_range(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-02T00:00:00Z",
                    }
                ]
            }
        )

        self.assertTrue(result["ok"])

    def test_gate_rejects_start_after_end(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "2024-01-03T00:00:00Z",
                        "end": "2024-01-02T00:00:00Z",
                    }
                ]
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].date_range_invalid", result["errors"])

    def test_gate_rejects_invalid_start_date(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "not-a-date",
                    }
                ]
            }
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].start_date_invalid", result["errors"])

    def test_missing_date_range_is_allowed(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "format": "json",
                        "size_bytes": 1,
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                    }
                ]
            }
        )

        self.assertTrue(result["ok"])

    def test_duplicate_dataset_warning_in_permissive_mode(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {"path": "a.json", "format": "json", "size_bytes": 1, "pair": "BTC/USDT", "timeframe": "1h"},
                    {"path": "b.json", "format": "json", "size_bytes": 1, "pair": "BTC/USDT", "timeframe": "1h"},
                ]
            },
            requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
        )

        self.assertTrue(result["ok"])
        self.assertIn(
            {"code": "duplicate_dataset_coverage", "pair": "BTC/USDT", "timeframe": "1h", "count": 2},
            result["warnings"],
        )

    def test_duplicate_dataset_error_in_strict_mode(self) -> None:
        result = run_inventory_manifest_gate(
            {
                "datasets": [
                    {"path": "a.json", "format": "json", "size_bytes": 1, "pair": "BTC/USDT", "timeframe": "1h"},
                    {"path": "b.json", "format": "json", "size_bytes": 1, "pair": "BTC/USDT", "timeframe": "1h"},
                ]
            },
            requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
            strict=True,
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "duplicate_dataset_coverage", "pair": "BTC/USDT", "timeframe": "1h", "count": 2},
            result["errors"],
        )

    def test_unknown_pair_timeframe_allowed_when_no_requirements(self) -> None:
        result = run_inventory_manifest_gate(
            {"datasets": [{"path": "notes.csv", "format": "csv", "size_bytes": 1}]}
        )

        self.assertTrue(result["ok"])

    def test_unknown_pair_timeframe_fails_in_strict_mode(self) -> None:
        result = run_inventory_manifest_gate(
            {"datasets": [{"path": "notes.csv", "format": "csv", "size_bytes": 1}]},
            strict=True,
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].pair_timeframe_unknown", result["errors"])


if __name__ == "__main__":
    unittest.main()

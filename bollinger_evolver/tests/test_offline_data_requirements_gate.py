"""Tests for pair/timeframe requirements coverage on offline inventory manifests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.data_gate import (
    build_requirements_coverage_matrix,
    check_manifest_requirements,
    extract_data_gate_error_codes,
    normalize_pair_symbol,
    normalize_timeframe,
    run_inventory_manifest_gate,
)
from bollinger_evolver.data_manifest import build_manifest_from_inventory
from bollinger_evolver.offline_data import inventory_offline_data


def _requirements(
    pairs: list[str] | None = None,
    timeframes: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "pairs": pairs or ["BTC/USDT", "ETH/USDT"],
        "timeframes": timeframes or ["1h", "4h"],
    }


class TestOfflineDataRequirementsGate(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _manifest(self, root: Path) -> dict[str, object]:
        return build_manifest_from_inventory(inventory_offline_data(root))

    def test_requirements_gate_passes_when_all_pair_timeframe_combinations_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for pair in ("BTC", "ETH"):
                for timeframe in ("1h", "4h"):
                    self._write(root, f"{pair}_USDT-{timeframe}.json")
            result = check_manifest_requirements(self._manifest(root), _requirements())

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_requirements_gate_fails_when_required_pair_timeframe_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            result = check_manifest_requirements(
                self._manifest(root),
                _requirements(pairs=["BTC/USDT"], timeframes=["1h", "4h"]),
            )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "4h"},
            result["errors"],
        )
        self.assertIn("missing_required_dataset", result["error_codes"])

    def test_requirements_gate_reports_all_missing_combinations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            result = check_manifest_requirements(self._manifest(root), _requirements())

        missing = [error for error in result["errors"] if error["code"] == "missing_required_dataset"]
        self.assertEqual(len(missing), 3)

    def test_requirements_gate_warns_for_duplicate_required_pair_timeframe_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "a/BTC_USDT-1h.json")
            self._write(root, "b/BTC_USDT-1h.csv")
            result = check_manifest_requirements(
                self._manifest(root),
                _requirements(pairs=["BTC/USDT"], timeframes=["1h"]),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])
        self.assertIn(
            {
                "code": "duplicate_dataset_coverage",
                "pair": "BTC/USDT",
                "timeframe": "1h",
                "count": 2,
            },
            result["warnings"],
        )

    def test_inventory_manifest_gate_preserves_duplicate_coverage_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "a/BTC_USDT-1h.json")
            self._write(root, "b/BTC_USDT-1h.csv")
            result = run_inventory_manifest_gate(
                self._manifest(root),
                requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
            )

        self.assertTrue(result["ok"])
        self.assertIn(
            {
                "code": "duplicate_dataset_coverage",
                "pair": "BTC/USDT",
                "timeframe": "1h",
                "count": 2,
            },
            result["warnings"],
        )

    def test_requirements_gate_rejects_empty_pairs(self) -> None:
        result = check_manifest_requirements({"datasets": []}, {"pairs": [], "timeframes": ["1h"]})

        self.assertFalse(result["ok"])
        self.assertIn({"code": "requirements_pairs_empty"}, result["errors"])

    def test_requirements_gate_rejects_empty_timeframes(self) -> None:
        result = check_manifest_requirements({"datasets": []}, {"pairs": ["BTC/USDT"], "timeframes": []})

        self.assertFalse(result["ok"])
        self.assertIn({"code": "requirements_timeframes_empty"}, result["errors"])

    def test_requirements_gate_rejects_invalid_pair(self) -> None:
        result = check_manifest_requirements(
            {"datasets": []},
            {"pairs": ["BTCUSDT"], "timeframes": ["1h"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn({"code": "requirements_pair_invalid", "pair": "BTCUSDT"}, result["errors"])

    def test_requirements_gate_normalizes_pair_symbols_before_coverage_check(self) -> None:
        result = check_manifest_requirements(
            {"datasets": [{"path": "BTC_USDT-1h.json", "pair": "BTC/USDT", "timeframe": "1h"}]},
            {"pairs": ["btc-usdt", "eth_usdt"], "timeframes": ["1h"]},
        )

        self.assertFalse(result["ok"])
        self.assertNotIn(
            {"code": "missing_required_dataset", "pair": "btc-usdt", "timeframe": "1h"},
            result["errors"],
        )
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "ETH/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_requirements_gate_normalizes_timeframes_before_coverage_check(self) -> None:
        result = check_manifest_requirements(
            {"datasets": [{"path": "BTC_USDT-1h.json", "pair": "BTC/USDT", "timeframe": "1h"}]},
            {"pairs": ["BTC/USDT"], "timeframes": ["1H", "4H"]},
        )

        self.assertFalse(result["ok"])
        self.assertNotIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "1H"},
            result["errors"],
        )
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "4h"},
            result["errors"],
        )

    def test_normalize_pair_symbol_accepts_common_pair_separators(self) -> None:
        self.assertEqual(normalize_pair_symbol("btc/usdt"), "BTC/USDT")
        self.assertEqual(normalize_pair_symbol("BTC-USDT"), "BTC/USDT")
        self.assertEqual(normalize_pair_symbol("btc_usdt"), "BTC/USDT")
        self.assertIsNone(normalize_pair_symbol("BTCUSDT"))

    def test_normalize_timeframe_accepts_uppercase_units(self) -> None:
        self.assertEqual(normalize_timeframe("15M"), "15m")
        self.assertEqual(normalize_timeframe("1H"), "1h")
        self.assertEqual(normalize_timeframe("4D"), "4d")
        self.assertIsNone(normalize_timeframe("fast"))

    def test_requirements_gate_rejects_invalid_timeframe(self) -> None:
        result = check_manifest_requirements(
            {"datasets": []},
            {"pairs": ["BTC/USDT"], "timeframes": ["fast"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn({"code": "requirements_timeframe_invalid", "timeframe": "fast"}, result["errors"])

    def test_requirements_gate_ignores_datasets_without_pair_or_timeframe_for_coverage(self) -> None:
        result = check_manifest_requirements(
            {
                "datasets": [
                    {"path": "notes.csv", "format": "csv", "size_bytes": 1, "pair": None, "timeframe": None}
                ]
            },
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_requirements_gate_preserves_existing_dataset_validation_errors(self) -> None:
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
                ]
            },
            requirements={"pairs": ["BTC/USDT"], "timeframes": ["4h"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].format_unsupported", result["errors"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "4h"},
            result["errors"],
        )
        self.assertEqual(
            result["error_codes"],
            ["datasets[0].format_unsupported", "missing_required_dataset"],
        )

    def test_coverage_matrix_marks_present_and_missing(self) -> None:
        matrix = build_requirements_coverage_matrix(
            {"datasets": [{"path": "BTC_USDT-1h.json", "pair": "BTC/USDT", "timeframe": "1h"}]},
            {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
        )

        self.assertTrue(matrix["ok"])
        self.assertEqual(
            matrix["matrix"],
            [
                {
                    "pair": "BTC/USDT",
                    "cells": [
                        {"timeframe": "1h", "status": "present"},
                        {"timeframe": "4h", "status": "missing"},
                    ],
                }
            ],
        )

    def test_coverage_matrix_ignores_extra_datasets(self) -> None:
        matrix = build_requirements_coverage_matrix(
            {
                "datasets": [
                    {"path": "BTC_USDT-1h.json", "pair": "BTC/USDT", "timeframe": "1h"},
                    {"path": "ETH_USDT-1h.json", "pair": "ETH/USDT", "timeframe": "1h"},
                ]
            },
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
        )

        self.assertEqual(matrix["pairs"], ["BTC/USDT"])
        self.assertEqual(len(matrix["matrix"]), 1)

    def test_coverage_matrix_sorts_pairs_and_timeframes(self) -> None:
        matrix = build_requirements_coverage_matrix(
            {"datasets": []},
            {"pairs": ["ETH/USDT", "BTC/USDT"], "timeframes": ["4h", "1h"]},
        )

        self.assertEqual(matrix["pairs"], ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(matrix["timeframes"], ["1h", "4h"])

    def test_coverage_matrix_rejects_invalid_requirements(self) -> None:
        matrix = build_requirements_coverage_matrix(
            {"datasets": []},
            {"pairs": ["BTCUSDT"], "timeframes": ["1h"]},
        )

        self.assertFalse(matrix["ok"])
        self.assertIn({"code": "requirements_pair_invalid", "pair": "BTCUSDT"}, matrix["errors"])

    def test_date_range_requirement_passes_when_dataset_covers_range(self) -> None:
        result = check_manifest_requirements(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-31T00:00:00Z",
                    }
                ]
            },
            {
                "pairs": ["BTC/USDT"],
                "timeframes": ["1h"],
                "start": "2024-01-05T00:00:00Z",
                "end": "2024-01-20T00:00:00Z",
            },
        )

        self.assertTrue(result["ok"])

    def test_date_range_requirement_fails_when_dataset_starts_too_late(self) -> None:
        result = check_manifest_requirements(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "2024-01-10T00:00:00Z",
                        "end": "2024-01-31T00:00:00Z",
                    }
                ]
            },
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"], "start": "2024-01-05T00:00:00Z"},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "dataset_starts_too_late", "pair": "BTC/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_date_range_requirement_fails_when_dataset_ends_too_early(self) -> None:
        result = check_manifest_requirements(
            {
                "datasets": [
                    {
                        "path": "BTC_USDT-1h.json",
                        "pair": "BTC/USDT",
                        "timeframe": "1h",
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-10T00:00:00Z",
                    }
                ]
            },
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"], "end": "2024-01-20T00:00:00Z"},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "dataset_ends_too_early", "pair": "BTC/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_date_range_requirement_fails_when_dataset_range_unknown(self) -> None:
        result = check_manifest_requirements(
            {"datasets": [{"path": "BTC_USDT-1h.json", "pair": "BTC/USDT", "timeframe": "1h"}]},
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"], "start": "2024-01-05T00:00:00Z"},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "dataset_date_range_missing", "pair": "BTC/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_requirements_gate_keeps_empty_manifest_as_datasets_empty(self) -> None:
        result = run_inventory_manifest_gate(
            {"datasets": []},
            requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn("datasets_empty", result["errors"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "1h"},
            result["errors"],
        )

    def test_extract_data_gate_error_codes_handles_string_and_mapping_errors(self) -> None:
        result = extract_data_gate_error_codes(
            [
                "datasets_empty",
                {"code": "missing_required_dataset", "pair": "BTC/USDT"},
                {"pair": "BTC/USDT"},
            ]
        )

        self.assertEqual(
            result,
            ["datasets_empty", "missing_required_dataset", "unknown_error"],
        )


if __name__ == "__main__":
    unittest.main()

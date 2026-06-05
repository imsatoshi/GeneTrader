"""Tests for the offline data manifest builder."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.data_manifest import (
    analyze_candles,
    build_offline_data_manifest,
    detect_data_file_format,
    infer_pair_timeframe_from_path,
    parse_candles_from_file,
)
from bollinger_evolver.data_quality import evaluate_data_coverage_gate


def _json_candles() -> list[list[object]]:
    return [
        [1714521600000, 100.0, 105.0, 99.0, 102.0, 10.0],
        [1714522500000, 102.0, 106.0, 101.0, 104.0, 10.0],
        [1714523400000, 104.0, 107.0, 103.0, 106.0, 10.0],
    ]


class TestDataManifestHelpers(unittest.TestCase):
    def test_detect_data_file_format(self) -> None:
        self.assertEqual(detect_data_file_format("BTC_USDT-15m.json"), "json")
        self.assertEqual(detect_data_file_format("BTC_USDT-15m.jsonl"), "jsonl")
        self.assertEqual(detect_data_file_format("BTC_USDT-15m.csv"), "csv")
        self.assertEqual(detect_data_file_format("BTC_USDT-15m.bin"), "unknown")

    def test_infer_pair_timeframe_from_path(self) -> None:
        pair, timeframe = infer_pair_timeframe_from_path("user_data/data/BTC_USDT-15m.json")
        self.assertEqual(pair, "BTC/USDT")
        self.assertEqual(timeframe, "15m")

    def test_analyze_candles_counts_duplicate_out_of_order_invalid_and_gaps(self) -> None:
        candles = [
            {"timestamp": 1714521600000, "open": 100, "high": 105, "low": 99, "close": 102},
            {"timestamp": 1714524300000, "open": 102, "high": 106, "low": 101, "close": 104},
            {"timestamp": 1714522500000, "open": 104, "high": 103, "low": 105, "close": 102},
            {"timestamp": 1714522500000, "open": 104, "high": 107, "low": 103, "close": 106},
        ]
        analysis = analyze_candles(candles, timeframe="15m")

        self.assertEqual(analysis["duplicate_timestamp_count"], 1)
        self.assertEqual(analysis["out_of_order_count"], 1)
        self.assertEqual(analysis["invalid_ohlc_count"], 1)
        self.assertEqual(analysis["gap_count"], 1)


class TestBuildOfflineDataManifest(unittest.TestCase):
    def _write_json_file(self, path: Path, rows: list[object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows), encoding="utf-8")

    def _write_csv_file(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_missing_data_dir_fails_without_crash(self) -> None:
        result = build_offline_data_manifest("missing-data-dir", write_report=False)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("data_dir_not_found", result["errors"])

    def test_empty_data_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_offline_data_manifest(temp_dir, write_report=False)

        self.assertEqual(result["status"], "EMPTY")
        self.assertIn("no_data_files_found", result["warnings"])

    def test_json_list_candles_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file_path = root / "BTC_USDT-15m.json"
            self._write_json_file(file_path, _json_candles())

            candles = parse_candles_from_file(file_path)
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["BTC/USDT"],
                timeframes=["15m"],
                write_report=False,
            )

        self.assertEqual(len(candles), 3)
        self.assertEqual(manifest["pair_timeframes"][0]["candle_count"], 3)

    def test_csv_candles_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            file_path = root / "ETH_USDT-1h.csv"
            self._write_csv_file(
                file_path,
                [
                    {
                        "timestamp": 1714521600,
                        "open": 200,
                        "high": 205,
                        "low": 198,
                        "close": 203,
                        "volume": 5,
                    },
                    {
                        "timestamp": 1714525200,
                        "open": 203,
                        "high": 206,
                        "low": 202,
                        "close": 205,
                        "volume": 5,
                    },
                ],
            )

            candles = parse_candles_from_file(file_path)
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["ETH/USDT"],
                timeframes=["1h"],
                write_report=False,
            )

        self.assertEqual(len(candles), 2)
        self.assertEqual(manifest["pair_timeframes"][0]["timeframe"], "1h")

    def test_manifest_counts_duplicate_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = _json_candles() + [[1714523400000, 104.0, 107.0, 103.0, 106.0, 10.0]]
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(temp_dir, write_report=False)

        self.assertEqual(manifest["pair_timeframes"][0]["duplicate_timestamp_count"], 1)

    def test_manifest_counts_out_of_order_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                [1714522500000, 100.0, 105.0, 99.0, 102.0, 10.0],
                [1714521600000, 102.0, 106.0, 101.0, 104.0, 10.0],
            ]
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(temp_dir, write_report=False)

        self.assertEqual(manifest["pair_timeframes"][0]["out_of_order_count"], 1)

    def test_manifest_counts_invalid_ohlc(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [[1714521600000, 100.0, 99.0, 101.0, 102.0, 10.0]]
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(temp_dir, write_report=False)

        self.assertEqual(manifest["pair_timeframes"][0]["invalid_ohlc_count"], 1)

    def test_manifest_counts_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = [
                [1714521600000, 100.0, 105.0, 99.0, 102.0, 10.0],
                [1714523400000, 102.0, 106.0, 101.0, 104.0, 10.0],
            ]
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(temp_dir, write_report=False)

        self.assertEqual(manifest["pair_timeframes"][0]["gap_count"], 1)

    def test_manifest_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "out"
            self._write_json_file(root / "BTC_USDT-15m.json", _json_candles())
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["BTC/USDT"],
                timeframes=["15m"],
                output_dir=str(out),
                write_report=True,
            )

            manifest_path = Path(manifest["manifest_path"])
            markdown_path = Path(manifest["markdown_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(markdown_path.exists())

    def test_manifest_is_compatible_with_data_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows: list[list[object]] = []
            base = 1714521600000
            for index in range(120):
                rows.append(
                    [base + (index * 900000), 100.0, 105.0, 99.0, 102.0, 10.0]
                )
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["BTC/USDT"],
                timeframes=["15m"],
                write_report=False,
            )
            gate = evaluate_data_coverage_gate(
                manifest,
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
                min_candles_per_pair_timeframe=100,
            )

        self.assertEqual(gate["status"], "PASS")

    def test_gate_fails_for_low_candle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_json_file(root / "BTC_USDT-15m.json", _json_candles())
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["BTC/USDT"],
                timeframes=["15m"],
                write_report=False,
            )
            gate = evaluate_data_coverage_gate(
                manifest,
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
                min_candles_per_pair_timeframe=100,
            )

        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("low_candle_count", gate["fail_reasons"])

    def test_gate_fails_for_missing_required_timeframe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows: list[list[object]] = []
            base = 1714521600000
            for index in range(120):
                rows.append(
                    [base + (index * 900000), 100.0, 105.0, 99.0, 102.0, 10.0]
                )
            self._write_json_file(root / "BTC_USDT-15m.json", rows)
            manifest = build_offline_data_manifest(
                temp_dir,
                pairs=["BTC/USDT"],
                timeframes=["15m", "1h"],
                write_report=False,
            )
            gate = evaluate_data_coverage_gate(
                manifest,
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m", "1h"],
                min_candles_per_pair_timeframe=100,
            )

        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("missing_pair_timeframe", gate["fail_reasons"])


if __name__ == "__main__":
    unittest.main()

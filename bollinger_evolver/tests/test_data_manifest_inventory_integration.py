"""Tests for building manifest-like payloads from offline inventory."""

from __future__ import annotations

import unittest

from bollinger_evolver.data_manifest import build_manifest_from_inventory, summarize_manifest


def _inventory() -> dict[str, object]:
    return {
        "root": "C:/tmp/offline",
        "files": [
            {
                "path": "BTC_USDT-1h.json",
                "format": "json",
                "size_bytes": 123,
                "pair": "BTC/USDT",
                "timeframe": "1h",
            },
            {
                "path": "ETH_USDT-5m.csv",
                "format": "csv",
                "size_bytes": 456,
                "pair": "ETH/USDT",
                "timeframe": "5m",
            },
        ],
    }


class TestManifestFromInventory(unittest.TestCase):
    def test_build_manifest_from_inventory_preserves_root(self) -> None:
        manifest = build_manifest_from_inventory(_inventory())

        self.assertEqual(manifest["root"], "C:/tmp/offline")

    def test_build_manifest_from_inventory_converts_files_to_datasets(self) -> None:
        manifest = build_manifest_from_inventory(_inventory())

        self.assertEqual(len(manifest["datasets"]), 2)
        self.assertEqual(manifest["datasets"][0]["path"], "BTC_USDT-1h.json")

    def test_build_manifest_from_inventory_preserves_pair_timeframe_format_size(self) -> None:
        manifest = build_manifest_from_inventory(_inventory())
        dataset = manifest["datasets"][0]

        self.assertEqual(dataset["pair"], "BTC/USDT")
        self.assertEqual(dataset["timeframe"], "1h")
        self.assertEqual(dataset["format"], "json")
        self.assertEqual(dataset["size_bytes"], 123)

    def test_build_manifest_from_inventory_preserves_stable_order(self) -> None:
        manifest = build_manifest_from_inventory(_inventory())

        self.assertEqual(
            [item["path"] for item in manifest["datasets"]],
            ["BTC_USDT-1h.json", "ETH_USDT-5m.csv"],
        )

    def test_build_manifest_from_inventory_handles_empty_inventory(self) -> None:
        manifest = build_manifest_from_inventory({"root": "C:/tmp/offline", "files": []})

        self.assertEqual(manifest["datasets"], [])

    def test_build_manifest_from_inventory_rejects_invalid_inventory_shape(self) -> None:
        with self.assertRaises(ValueError):
            build_manifest_from_inventory({"root": "C:/tmp/offline"})

    def test_summarize_manifest_counts_datasets(self) -> None:
        summary = summarize_manifest(build_manifest_from_inventory(_inventory()))

        self.assertEqual(summary["dataset_count"], 2)

    def test_summarize_manifest_lists_pairs_timeframes(self) -> None:
        summary = summarize_manifest(build_manifest_from_inventory(_inventory()))

        self.assertEqual(summary["pairs"], ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(summary["timeframes"], ["1h", "5m"])

    def test_summarize_manifest_counts_missing_pair_timeframe(self) -> None:
        summary = summarize_manifest(
            {
                "pair_timeframes": [],
                "coverage_summary": {
                    "missing_pair_timeframes": [
                        {"pair": "BTC/USDT", "timeframe": "1h"},
                        {"pair": "BTC/USDT", "timeframe": "4h"},
                    ]
                },
            }
        )

        self.assertEqual(summary["missing_pair_timeframe_count"], 2)

    def test_summarize_manifest_handles_invalid_shape_gracefully(self) -> None:
        summary = summarize_manifest(["not", "a", "mapping"])

        self.assertFalse(summary["valid"])
        self.assertEqual(summary["dataset_count"], 0)


if __name__ == "__main__":
    unittest.main()

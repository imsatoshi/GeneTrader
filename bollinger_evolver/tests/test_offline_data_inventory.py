"""Tests for metadata-only offline data inventory."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.offline_data import inventory_offline_data
from bollinger_evolver.offline_data import summarize_inventory


class TestOfflineDataInventory(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_inventory_scans_supported_files_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "nested/BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(len(inventory["files"]), 1)
        self.assertEqual(inventory["files"][0]["path"], "nested/BTC_USDT-1h.json")

    def test_inventory_ignores_unsupported_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.txt")
            self._write(root, "BTC_USDT-1h.csv")
            inventory = inventory_offline_data(root)

        self.assertEqual([item["path"] for item in inventory["files"]], ["BTC_USDT-1h.csv"])

    def test_inventory_supports_json_gz_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "SOL_USDT-1d.json.gz")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["format"], "json.gz")
        self.assertEqual(inventory["files"][0]["pair"], "SOL/USDT")
        self.assertEqual(inventory["files"][0]["timeframe"], "1d")

    def test_inventory_accepts_uppercase_json_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.JSON")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["format"], "json")

    def test_inventory_accepts_uppercase_csv_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.CSV")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["format"], "csv")

    def test_inventory_accepts_uppercase_json_gz_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.JSON.GZ")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["format"], "json.gz")

    def test_inventory_returns_stable_sorted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(
            [item["path"] for item in inventory["files"]],
            ["a/BTC_USDT-1h.json", "z/ETH_USDT-5m.csv"],
        )

    def test_inventory_paths_use_forward_slashes_for_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "nested/deeper/BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["path"], "nested/deeper/BTC_USDT-1h.json")

    def test_inventory_sort_order_is_stable_for_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "b/BTC_USDT-1h.json")
            self._write(root, "a/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-4h.csv")
            inventory = inventory_offline_data(root)

        self.assertEqual(
            [item["path"] for item in inventory["files"]],
            ["a/BTC_USDT-4h.csv", "a/ETH_USDT-5m.csv", "b/BTC_USDT-1h.json"],
        )

    def test_inventory_extracts_pair_and_timeframe_from_freqtrade_like_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "ETH_USDT-5m.csv")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["pair"], "ETH/USDT")
        self.assertEqual(inventory["files"][0]["timeframe"], "5m")

    def test_inventory_extracts_pair_from_hyphenated_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC-USDT-1h.csv")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["pair"], "BTC/USDT")
        self.assertEqual(inventory["files"][0]["timeframe"], "1h")

    def test_inventory_extracts_pair_from_underscore_timeframe_separator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT_4h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["pair"], "BTC/USDT")
        self.assertEqual(inventory["files"][0]["timeframe"], "4h")

    def test_inventory_normalizes_uppercase_timeframe_unit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1M.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["pair"], "BTC/USDT")
        self.assertEqual(inventory["files"][0]["timeframe"], "1m")

    def test_inventory_rejects_filename_when_timeframe_is_not_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h-backup.csv")
            inventory = inventory_offline_data(root)

        self.assertIsNone(inventory["files"][0]["pair"])
        self.assertIsNone(inventory["files"][0]["timeframe"])

    def test_inventory_rejects_ambiguous_multi_pair_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT_ETH-1h.csv")
            inventory = inventory_offline_data(root)

        self.assertIsNone(inventory["files"][0]["pair"])
        self.assertIsNone(inventory["files"][0]["timeframe"])

    def test_inventory_uses_none_for_unrecognized_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "notes.csv")
            inventory = inventory_offline_data(root)

        self.assertIsNone(inventory["files"][0]["pair"])
        self.assertIsNone(inventory["files"][0]["timeframe"])

    def test_inventory_does_not_follow_symlink_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = self._write(root, "BTC_USDT-1h.json")
            link = root / "ETH_USDT-1h.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            inventory = inventory_offline_data(root)

        self.assertEqual([item["path"] for item in inventory["files"]], ["BTC_USDT-1h.json"])
        self.assertIn(
            {"path": "ETH_USDT-1h.json", "reason": "symlink_ignored"},
            inventory["warnings"],
        )

    def test_inventory_regular_files_still_scanned_when_symlink_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = self._write(root, "BTC_USDT-1h.json")
            link = root / "BTC_USDT-4h.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            inventory = inventory_offline_data(root)

        self.assertEqual(len(inventory["files"]), 1)
        self.assertEqual(inventory["files"][0]["path"], "BTC_USDT-1h.json")

    def test_inventory_ignores_dotfiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, ".BTC_USDT-1h.json")
            self._write(root, ".hidden/BTC_USDT-4h.csv")
            self._write(root, "BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual([item["path"] for item in inventory["files"]], ["BTC_USDT-1h.json"])

    def test_inventory_ignores_tmp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json.tmp")
            self._write(root, "BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual([item["path"] for item in inventory["files"]], ["BTC_USDT-1h.json"])

    def test_inventory_ignores_backup_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json.bak")
            self._write(root, "BTC_USDT-1h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual([item["path"] for item in inventory["files"]], ["BTC_USDT-1h.json"])

    def test_inventory_respects_max_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            self._write(root, "BTC_USDT-4h.json")
            inventory = inventory_offline_data(root, max_files=1)

        self.assertEqual(len(inventory["files"]), 1)
        self.assertIn(
            {"code": "too_many_files", "max_files": 1, "scanned_files": 2},
            inventory["warnings"],
        )

    def test_inventory_without_max_files_preserves_existing_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            self._write(root, "BTC_USDT-4h.json")
            inventory = inventory_offline_data(root)

        self.assertEqual(len(inventory["files"]), 2)

    def test_inventory_max_files_rejects_zero_or_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_files_must_be_positive"):
            inventory_offline_data("unused", max_files=0)

    def test_inventory_ignored_files_omitted_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "README.txt")
            inventory = inventory_offline_data(root)

        self.assertNotIn("ignored_files", inventory)

    def test_inventory_can_include_ignored_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "README.txt")
            inventory = inventory_offline_data(root, include_ignored=True)

        self.assertEqual(
            inventory["ignored_files"],
            [{"path": "README.txt", "reason": "unsupported_format"}],
        )

    def test_inventory_ignored_file_has_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json.tmp")
            inventory = inventory_offline_data(root, include_ignored=True)

        self.assertEqual(
            inventory["ignored_files"],
            [{"path": "BTC_USDT-1h.json.tmp", "reason": "hidden_or_temp_file"}],
        )

    def test_inventory_probe_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", b"timestamp,open,high,low,close,volume\n")
            inventory = inventory_offline_data(root)

        self.assertNotIn("probe", inventory["files"][0])

    def test_csv_probe_is_metadata_only_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(
                root,
                "BTC_USDT-1h.csv",
                b"timestamp,open,high,low,close,volume\n1,2,3,4,5,6\n",
            )
            inventory = inventory_offline_data(root, probe=True, max_probe_bytes=40)

        probe = inventory["files"][0]["probe"]
        self.assertFalse(probe["enabled"])
        self.assertTrue(probe["metadata_only"])
        self.assertEqual(probe["format"], "csv")
        self.assertEqual(probe["reason"], "content_probe_disabled_metadata_only")
        self.assertNotIn("columns", probe)

    def test_json_probe_is_metadata_only_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(
                root,
                "BTC_USDT-1h.json",
                b'[{"timestamp":1,"open":2,"high":3,"low":1,"close":2,"volume":5}]',
            )
            inventory = inventory_offline_data(root, probe=True)

        probe = inventory["files"][0]["probe"]
        self.assertFalse(probe["enabled"])
        self.assertTrue(probe["metadata_only"])
        self.assertEqual(probe["format"], "json")
        self.assertNotIn("row_count_estimate", probe)

    def test_feather_parquet_probe_is_metadata_only_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.parquet", b"not-real-parquet")
            inventory = inventory_offline_data(root, probe=True)

        probe = inventory["files"][0]["probe"]
        self.assertFalse(probe["enabled"])
        self.assertTrue(probe["metadata_only"])
        self.assertEqual(probe["format"], "parquet")
        self.assertEqual(probe["size_bytes"], len(b"not-real-parquet"))

    def test_probe_respects_max_probe_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(
                root,
                "BTC_USDT-1h.csv",
                b"timestamp,open,high,low,close,volume\n1,2,3,4,5,6\n",
            )
            inventory = inventory_offline_data(root, probe=True, max_probe_bytes=8)

        probe = inventory["files"][0]["probe"]
        self.assertEqual(probe["max_probe_bytes"], 8)
        self.assertTrue(probe["metadata_only"])
        self.assertEqual(probe["reason"], "content_probe_disabled_metadata_only")

    def test_summarize_inventory_counts_files(self) -> None:
        inventory = {"files": [{"path": "a", "pair": "BTC/USDT", "timeframe": "1h", "size_bytes": 3}]}

        self.assertEqual(summarize_inventory(inventory)["file_count"], 1)

    def test_summarize_inventory_sums_size(self) -> None:
        inventory = {
            "files": [
                {"path": "a", "pair": "BTC/USDT", "timeframe": "1h", "size_bytes": 3},
                {"path": "b", "pair": None, "timeframe": None, "size_bytes": 4},
            ]
        }

        self.assertEqual(summarize_inventory(inventory)["total_size_bytes"], 7)

    def test_summarize_inventory_lists_unique_pairs_sorted(self) -> None:
        inventory = {
            "files": [
                {"path": "b", "pair": "ETH/USDT", "timeframe": "4h", "size_bytes": 1},
                {"path": "a", "pair": "BTC/USDT", "timeframe": "1h", "size_bytes": 1},
            ]
        }

        summary = summarize_inventory(inventory)
        self.assertEqual(summary["pairs"], ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(summary["timeframes"], ["1h", "4h"])

    def test_summarize_inventory_counts_unparsed_files(self) -> None:
        inventory = {
            "files": [
                {"path": "a", "pair": None, "timeframe": None, "size_bytes": 1},
                {"path": "b", "pair": "BTC/USDT", "timeframe": "1h", "size_bytes": 1},
            ]
        }

        self.assertEqual(summarize_inventory(inventory)["unparsed_file_count"], 1)

    def test_summarize_inventory_handles_empty_inventory(self) -> None:
        summary = summarize_inventory({"files": []})

        self.assertEqual(summary["file_count"], 0)
        self.assertEqual(summary["pairs"], [])

    def test_inventory_records_size_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json", b"abcdef")
            inventory = inventory_offline_data(root)

        self.assertEqual(inventory["files"][0]["size_bytes"], 6)

    def test_inventory_reports_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            inventory = inventory_offline_data(missing)

        self.assertEqual(inventory["files"], [])
        self.assertEqual(inventory["errors"], ["root_not_found"])


if __name__ == "__main__":
    unittest.main()

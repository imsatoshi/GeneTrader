"""Windows path compatibility tests for offline data metadata outputs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.offline_data import inventory_offline_data
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_paths import normalize_offline_relative_path, offline_path_sort_key
from bollinger_evolver.preflight import build_offline_data_preflight_report


class TestOfflineDataWindowsPaths(unittest.TestCase):
    def _write(self, root: Path, name: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
        return path

    def test_normalize_offline_relative_path_removes_drive_and_backslashes(self) -> None:
        self.assertEqual(
            normalize_offline_relative_path(r"C:\data\BTC_USDT-1h.csv"),
            "data/BTC_USDT-1h.csv",
        )
        self.assertEqual(normalize_offline_relative_path(r".\a\b.json"), "a/b.json")

    def test_offline_path_sort_key_is_case_stable(self) -> None:
        paths = ["B/eth.csv", "a/BTC.csv", "A/ada.csv"]
        self.assertEqual(
            sorted(paths, key=offline_path_sort_key),
            ["A/ada.csv", "a/BTC.csv", "B/eth.csv"],
        )

    def test_inventory_and_report_dataset_paths_use_relative_forward_slashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "nested/BTC_USDT-1h.csv")
            inventory = inventory_offline_data(root)
            report = build_offline_data_preflight_report(root).to_dict()

        self.assertEqual(inventory["files"][0]["path"], "nested/BTC_USDT-1h.csv")
        dataset = report["datasets"][0]
        self.assertEqual(dataset["relative_path"], "nested/BTC_USDT-1h.csv")
        self.assertNotIn("\\", dataset["relative_path"])
        self.assertNotIn(":", dataset["relative_path"])

    def test_diff_identity_prefers_normalized_relative_path(self) -> None:
        old = {
            "datasets": [
                {
                    "relative_path": r"a\BTC_USDT-1h.csv",
                    "path": r"C:\tmp\a\BTC_USDT-1h.csv",
                    "suffix": ".csv",
                    "size_bytes": 1,
                }
            ]
        }
        new = {
            "datasets": [
                {
                    "relative_path": "a/BTC_USDT-1h.csv",
                    "path": r"D:\other\a\BTC_USDT-1h.csv",
                    "suffix": ".csv",
                    "size_bytes": 1,
                }
            ]
        }
        diff = compare_offline_data_preflight_reports(old, new)

        self.assertEqual(diff.unchanged_count, 1)
        self.assertEqual(diff.added_datasets, [])
        self.assertEqual(diff.removed_datasets, [])


if __name__ == "__main__":
    unittest.main()

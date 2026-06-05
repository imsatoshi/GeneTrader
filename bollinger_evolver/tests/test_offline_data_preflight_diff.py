"""Tests for offline data preflight report diffing."""

from __future__ import annotations

import builtins
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.preflight import build_offline_data_preflight_report


class TestOfflineDataPreflightDiff(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _report(self, root: Path):
        return build_offline_data_preflight_report(root)

    def test_added_file(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "BTC_USDT-1h.json")
            self._write(new_root, "BTC_USDT-1h.json")
            self._write(new_root, "ETH_USDT-5m.csv")
            diff = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root))

        self.assertEqual([item["relative_path"] for item in diff.added_datasets], ["ETH_USDT-5m.csv"])

    def test_removed_file(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "BTC_USDT-1h.json")
            self._write(old_root, "ETH_USDT-5m.csv")
            self._write(new_root, "BTC_USDT-1h.json")
            diff = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root))

        self.assertEqual([item["relative_path"] for item in diff.removed_datasets], ["ETH_USDT-5m.csv"])

    def test_changed_size(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "BTC_USDT-1h.json", b"x")
            self._write(new_root, "BTC_USDT-1h.json", b"xx")
            diff = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root))

        self.assertEqual(diff.changed_datasets[0]["changed_fields"], ["size_bytes"])

    def test_unchanged_file(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "BTC_USDT-1h.json", b"x")
            self._write(new_root, "BTC_USDT-1h.json", b"x")
            diff = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root))

        self.assertEqual(diff.unchanged_count, 1)

    def test_deterministic_json(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "z/ETH_USDT-5m.csv")
            self._write(new_root, "a/BTC_USDT-1h.json")
            first = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root)).to_json()
            second = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root)).to_json()

        self.assertEqual(first, second)

    def test_dict_input(self) -> None:
        old = {"datasets": [], "summary": {"scanned_files": 0}}
        new = {
            "datasets": [{"relative_path": "BTC_USDT-1h.json", "size_bytes": 1, "suffix": ".json", "file_type": "json"}],
            "summary": {"scanned_files": 1},
        }
        diff = compare_offline_data_preflight_reports(old, new)

        self.assertEqual(len(diff.added_datasets), 1)

    def test_report_object_input(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            self._write(old_root, "BTC_USDT-1h.json")
            self._write(new_root, "BTC_USDT-1h.json")
            diff = compare_offline_data_preflight_reports(self._report(old_root), self._report(new_root))

        self.assertTrue(diff.ok)

    def test_secret_payload_does_not_leak(self) -> None:
        marker = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"
        old = {
            "datasets": [
                {
                    "relative_path": "BTC_USDT-1h.json",
                    "size_bytes": 1,
                    "suffix": ".json",
                    "file_type": "json",
                    "content": marker,
                }
            ],
            "summary": {"scanned_files": 1},
        }
        new = {"datasets": [], "summary": {"scanned_files": 0}}
        diff = compare_offline_data_preflight_reports(old, new)

        self.assertNotIn(marker, diff.to_json())

    def test_diff_does_not_read_file_contents(self) -> None:
        old = {
            "datasets": [{"relative_path": "BTC_USDT-1h.json", "size_bytes": 1, "suffix": ".json", "file_type": "json"}]
        }
        new = {
            "datasets": [{"relative_path": "BTC_USDT-1h.json", "size_bytes": 2, "suffix": ".json", "file_type": "json"}]
        }
        with patch.object(Path, "read_text", side_effect=AssertionError("content read")):
            with patch.object(builtins, "open", side_effect=AssertionError("content read")):
                diff = compare_offline_data_preflight_reports(old, new)

        self.assertEqual(len(diff.changed_datasets), 1)

    def test_import_bollinger_evolver_safe(self) -> None:
        import bollinger_evolver

        self.assertTrue(callable(bollinger_evolver.compare_offline_data_preflight_reports))


if __name__ == "__main__":
    unittest.main()

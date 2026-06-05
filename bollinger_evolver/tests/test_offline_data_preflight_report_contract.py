"""Tests for the offline data preflight report contract."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.preflight import (
    OfflineDataPreflightReport,
    build_offline_data_preflight_report,
    run_offline_data_preflight,
)


class TestOfflineDataPreflightReportContract(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_report_can_to_dict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            report = build_offline_data_preflight_report(root)

        payload = report.to_dict()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["accepted_files"], 1)
        self.assertEqual(payload["datasets"][0]["relative_path"], "BTC_USDT-1h.json")

    def test_report_can_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            report = build_offline_data_preflight_report(root)

        payload = json.loads(report.to_json())
        self.assertEqual(payload["accepted_files"], 1)
        self.assertEqual(payload["metadata"]["inventory_source"], "metadata_only")

    def test_report_json_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            first = build_offline_data_preflight_report(root).to_json()
            second = build_offline_data_preflight_report(root).to_json()

        self.assertEqual(first, second)

    def test_empty_directory_report_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_offline_data_preflight_report(temp_dir)

        self.assertFalse(report.ok)
        self.assertEqual(report.scanned_files, 0)
        self.assertEqual(report.datasets, [])
        self.assertTrue(report.issues)

    def test_multi_file_directory_order_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            report = build_offline_data_preflight_report(root)

        self.assertEqual(
            [item["relative_path"] for item in report.datasets],
            ["a/BTC_USDT-1h.json", "z/ETH_USDT-5m.csv"],
        )

    def test_rejected_warning_issue_counts_are_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            self._write(root, "README.txt")
            self._write(root, "ETH_USDT-5m.csv", b"")
            report = build_offline_data_preflight_report(root)

        self.assertFalse(report.ok)
        self.assertEqual(report.accepted_files, 2)
        self.assertEqual(report.rejected_files, 1)
        self.assertEqual(report.scanned_files, 3)
        self.assertEqual(len(report.warnings), 1)
        self.assertTrue(report.issues)

    def test_report_does_not_read_file_contents(self) -> None:
        marker = b"SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", marker)
            with patch.object(Path, "read_text", side_effect=AssertionError("content read")):
                report = build_offline_data_preflight_report(root)

        self.assertTrue(report.ok)
        self.assertNotIn(marker.decode("ascii"), report.to_json())
        self.assertNotIn(marker.decode("ascii"), str(report.to_dict()))

    def test_run_offline_data_preflight_keeps_legacy_shape_and_adds_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            result = run_offline_data_preflight(root)

        self.assertIn("inventory", result)
        self.assertIn("manifest", result)
        self.assertIn("gate", result)
        self.assertIn("report", result)
        self.assertTrue(result["report"]["ok"])

    def test_report_round_trips_from_dict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            report = build_offline_data_preflight_report(root)
            restored = OfflineDataPreflightReport.from_dict(report.to_dict())

        self.assertEqual(restored.to_json(), report.to_json())


if __name__ == "__main__":
    unittest.main()

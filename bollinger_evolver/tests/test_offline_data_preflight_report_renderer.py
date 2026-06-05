"""Tests for offline data preflight report renderers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    render_offline_data_preflight_report,
)


class TestOfflineDataPreflightReportRenderer(unittest.TestCase):
    def test_render_text_report_contains_summary_and_issue_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_offline_data_preflight_report(Path(temp_dir))
            rendered = render_offline_data_preflight_report(report, output_format="text")

        self.assertIn("Offline Data Preflight Report", rendered)
        self.assertIn("status: FAIL", rendered)
        self.assertIn("datasets_empty", rendered)

    def test_render_markdown_report_contains_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            report = build_offline_data_preflight_report(root)
            rendered = render_offline_data_preflight_report(report, output_format="markdown")

        self.assertIn("# Offline Data Preflight Report", rendered)
        self.assertIn("## Summary", rendered)
        self.assertIn("## Issues", rendered)
        self.assertIn("## Warnings", rendered)
        self.assertIn("## Coverage Matrix", rendered)
        self.assertIn("## Datasets", rendered)
        self.assertIn("BTC_USDT-1h.json", rendered)

    def test_render_accepts_report_dict_payload(self) -> None:
        payload = {
            "ok": True,
            "root": "data",
            "scanned_files": 0,
            "accepted_files": 0,
            "rejected_files": 0,
            "issues": [],
            "warnings": [],
            "datasets": [],
        }

        rendered = render_offline_data_preflight_report(payload)

        self.assertIn("status: PASS", rendered)
        self.assertIn("root: data", rendered)

    def test_render_rejects_unknown_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported_report_format"):
            render_offline_data_preflight_report({"ok": True}, output_format="html")

    def test_report_includes_coverage_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            report = build_offline_data_preflight_report(
                root,
                requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )
            rendered = render_offline_data_preflight_report(report, output_format="markdown")

        self.assertIn("| Pair | 1h | 4h |", rendered)

    def test_report_marks_present_and_missing_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            report = build_offline_data_preflight_report(
                root,
                requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )
            rendered = render_offline_data_preflight_report(report, output_format="text")

        self.assertIn("1h: present", rendered)
        self.assertIn("4h: missing", rendered)

    def test_report_handles_no_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_offline_data_preflight_report(Path(temp_dir))
            rendered = render_offline_data_preflight_report(report, output_format="text")

        self.assertIn("no requirements coverage matrix", rendered)


if __name__ == "__main__":
    unittest.main()

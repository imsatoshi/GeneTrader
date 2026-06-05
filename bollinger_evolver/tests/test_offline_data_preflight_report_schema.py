"""Schema-hardening tests for offline data preflight reports."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.preflight import (
    OfflineDataPreflightReport,
    build_offline_data_preflight_report,
    validate_offline_data_preflight_report_dict,
)


class TestOfflineDataPreflightReportSchema(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _report_dict(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            return build_offline_data_preflight_report(root).to_dict()

    def test_current_report_dict_passes_validation(self) -> None:
        issues = validate_offline_data_preflight_report_dict(self._report_dict())

        self.assertEqual(issues, [])

    def test_missing_required_key_produces_error_issue(self) -> None:
        payload = self._report_dict()
        payload.pop("datasets")
        issues = validate_offline_data_preflight_report_dict(payload)

        self.assertTrue(any(issue.code == "missing_required_key" for issue in issues))

    def test_invalid_severity_produces_error_issue(self) -> None:
        payload = self._report_dict()
        payload["issues"] = [{"code": "x", "message": "x", "path": None, "severity": "info"}]
        issues = validate_offline_data_preflight_report_dict(payload)

        self.assertTrue(any(issue.code == "invalid_issue_severity" for issue in issues))

    def test_non_int_counters_produce_error_issue(self) -> None:
        payload = self._report_dict()
        payload["accepted_files"] = "1"
        issues = validate_offline_data_preflight_report_dict(payload)

        self.assertTrue(any(issue.code == "invalid_counter" for issue in issues))

    def test_from_dict_reads_stage_012_shape(self) -> None:
        old_payload = {
            "ok": True,
            "root": "root",
            "scanned_files": 1,
            "accepted_files": 1,
            "rejected_files": 0,
            "total_size_bytes": 1,
            "datasets": [],
            "issues": [],
            "warnings": [],
            "metadata": {},
        }

        report = OfflineDataPreflightReport.from_dict(old_payload)

        self.assertEqual(report.schema_name, "offline_data_preflight_report")
        self.assertEqual(report.schema_version, "1.0")

    def test_to_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            first = build_offline_data_preflight_report(root).to_json()
            second = build_offline_data_preflight_report(root).to_json()

        self.assertEqual(first, second)

    def test_secret_payload_does_not_leak(self) -> None:
        marker = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", marker.encode("ascii"))
            report = build_offline_data_preflight_report(root)

        self.assertNotIn(marker, report.to_json())
        self.assertNotIn(marker, str(report.to_dict()))

    def test_report_builder_does_not_read_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", b"content should not be read")
            with patch.object(Path, "read_text", side_effect=AssertionError("content read")):
                report = build_offline_data_preflight_report(root)

        self.assertTrue(report.ok)

    def test_unserializable_value_produces_error_issue(self) -> None:
        payload = self._report_dict()
        payload["metadata"] = {"bad": object()}
        issues = validate_offline_data_preflight_report_dict(payload)

        self.assertTrue(any(issue.code == "not_json_serializable" for issue in issues))


if __name__ == "__main__":
    unittest.main()

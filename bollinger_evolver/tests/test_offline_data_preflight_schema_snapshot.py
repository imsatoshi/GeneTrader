"""Schema snapshot tests for offline data preflight results."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    run_offline_data_preflight,
)


class TestOfflineDataPreflightSchemaSnapshot(unittest.TestCase):
    def test_run_offline_data_preflight_result_top_level_schema_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_preflight(Path(temp_dir))

        self.assertEqual(
            sorted(result.keys()),
            [
                "error_codes",
                "errors",
                "gate",
                "inventory",
                "manifest",
                "ok",
                "report",
                "requirements",
            ],
        )
        self.assertIsInstance(result["ok"], bool)
        self.assertIsInstance(result["errors"], list)
        self.assertIsInstance(result["error_codes"], list)
        self.assertIsInstance(result["requirements"], dict)

    def test_offline_data_preflight_report_schema_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_offline_data_preflight_report(Path(temp_dir)).to_dict()

        self.assertEqual(
            sorted(report.keys()),
            [
                "accepted_files",
                "datasets",
                "generated_by",
                "issues",
                "metadata",
                "ok",
                "rejected_files",
                "root",
                "scanned_files",
                "schema_name",
                "schema_version",
                "summary",
                "total_size_bytes",
                "warnings",
            ],
        )
        self.assertEqual(report["schema_name"], "offline_data_preflight_report")
        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(report["generated_by"], "bollinger_evolver")

    def test_offline_data_preflight_outputs_are_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_preflight(Path(temp_dir))
            report = build_offline_data_preflight_report(Path(temp_dir))

        json.dumps(result, sort_keys=True)
        json.dumps(report.to_dict(), sort_keys=True)
        json.loads(report.to_json())


if __name__ == "__main__":
    unittest.main()

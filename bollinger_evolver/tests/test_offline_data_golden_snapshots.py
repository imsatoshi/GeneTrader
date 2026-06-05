"""Golden snapshot-style regression tests for offline data metadata-only flows."""

from __future__ import annotations

import builtins
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_backtest_gate import run_backtest_offline_data_gate
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_data_summary import (
    format_offline_data_diff_summary,
    format_offline_data_preflight_summary,
)
from bollinger_evolver.offline_release import run_offline_data_release_readiness_audit
from bollinger_evolver.offline_workflow import run_offline_data_workflow_preflight
from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    validate_offline_data_preflight_report_dict,
)


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataGoldenSnapshots(unittest.TestCase):
    def _write_tree(self, root: Path) -> set[Path]:
        paths = [
            root / "alpha.csv",
            root / "nested" / "beta.json",
            root / "nested" / "gamma.json.gz",
            root / "prices" / "delta.feather",
            root / "prices" / "epsilon.parquet",
        ]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PAYLOAD, encoding="utf-8")
        return {path.resolve() for path in paths}

    def _older_report(self, report_dict: dict[str, object]) -> dict[str, object]:
        by_path = {
            item["relative_path"]: dict(item)
            for item in report_dict["datasets"]
            if isinstance(item, dict)
        }
        beta = dict(by_path["nested/beta.json"])
        beta["relative_path"] = "nested\\beta.json"
        beta["path"] = "nested\\beta.json"
        beta["size_bytes"] = 1
        delta = dict(by_path["prices/delta.feather"])
        delta["relative_path"] = "prices\\delta.feather"
        delta["path"] = "prices\\delta.feather"
        delta["size_bytes"] = 1
        older = json.loads(json.dumps(report_dict, sort_keys=True))
        older["datasets"] = [
            {
                "relative_path": "zeta.csv",
                "path": "zeta.csv",
                "suffix": ".csv",
                "file_type": "csv",
                "format": "csv",
                "size_bytes": 1,
                "pair": None,
                "timeframe": None,
            },
            delta,
            {
                "relative_path": "removed\\omega.csv",
                "path": "removed\\omega.csv",
                "suffix": ".csv",
                "file_type": "csv",
                "format": "csv",
                "size_bytes": 1,
                "pair": None,
                "timeframe": None,
            },
            beta,
        ]
        older["summary"] = {
            "scanned_files": 4,
            "accepted_files": 4,
            "rejected_files": 0,
            "total_size_bytes": 4,
        }
        return older

    def _guard_fake_reads(self, data_files: set[Path]):
        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes
        original_open = builtins.open

        def guarded_read_text(path: Path, *args, **kwargs):
            if path.resolve() in data_files:
                raise AssertionError("fake market file content should not be read")
            return original_read_text(path, *args, **kwargs)

        def guarded_read_bytes(path: Path, *args, **kwargs):
            if path.resolve() in data_files:
                raise AssertionError("fake market file content should not be read")
            return original_read_bytes(path, *args, **kwargs)

        def guarded_open(file, mode="r", *args, **kwargs):
            if "r" in mode:
                try:
                    if Path(file).resolve() in data_files:
                        raise AssertionError("fake market file content should not be read")
                except (TypeError, OSError):
                    pass
            return original_open(file, mode, *args, **kwargs)

        return (
            patch.object(Path, "read_text", guarded_read_text),
            patch.object(Path, "read_bytes", guarded_read_bytes),
            patch.object(builtins, "open", guarded_open),
        )

    def test_golden_snapshot_outputs_are_stable_and_metadata_only(self) -> None:
        payload_size = len(PAYLOAD.encode("utf-8"))
        expected_paths = [
            "alpha.csv",
            "nested/beta.json",
            "nested/gamma.json.gz",
            "prices/delta.feather",
            "prices/epsilon.parquet",
        ]
        expected_keys = {
            "ok",
            "root",
            "scanned_files",
            "accepted_files",
            "rejected_files",
            "total_size_bytes",
            "summary",
            "datasets",
            "issues",
            "warnings",
            "metadata",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_tree(root)
            read_text_patch, read_bytes_patch, open_patch = self._guard_fake_reads(data_files)

            with read_text_patch, read_bytes_patch, open_patch:
                report = build_offline_data_preflight_report(root)
                report_again = build_offline_data_preflight_report(root)
                report_dict = report.to_dict()
                report_dict_again = report_again.to_dict()
                report_json = report.to_json()
                report_json_again = report_again.to_json()
                validation = [item.to_dict() for item in validate_offline_data_preflight_report_dict(report_dict)]
                validation_again = [
                    item.to_dict()
                    for item in validate_offline_data_preflight_report_dict(report_dict_again)
                ]
                older_report = self._older_report(report_dict)
                diff = compare_offline_data_preflight_reports(older_report, report)
                diff_again = compare_offline_data_preflight_reports(older_report, report_again)
                summary = format_offline_data_preflight_summary(
                    report,
                    include_datasets=True,
                    max_datasets=10,
                )
                summary_again = format_offline_data_preflight_summary(
                    report_again,
                    include_datasets=True,
                    max_datasets=10,
                )
                diff_summary = format_offline_data_diff_summary(diff)
                diff_summary_again = format_offline_data_diff_summary(diff_again)
                workflow = run_offline_data_workflow_preflight(root)
                workflow_again = run_offline_data_workflow_preflight(root)
                backtest_gate = run_backtest_offline_data_gate(root)
                backtest_gate_again = run_backtest_offline_data_gate(root)
                release_audit = run_offline_data_release_readiness_audit()
                release_audit_again = run_offline_data_release_readiness_audit()

        self.assertEqual(report_json, report_json_again)
        self.assertEqual(report_dict, report_dict_again)
        self.assertEqual(validation, validation_again)
        self.assertEqual(diff.to_json(), diff_again.to_json())
        self.assertEqual(diff.to_dict(), diff_again.to_dict())
        self.assertEqual(summary, summary_again)
        self.assertEqual(diff_summary, diff_summary_again)
        self.assertEqual(workflow, workflow_again)
        self.assertEqual(backtest_gate, backtest_gate_again)
        self.assertEqual(release_audit, release_audit_again)

        self.assertTrue(expected_keys.issubset(report_dict))
        self.assertEqual(report_dict["schema_version"], "1.0")
        self.assertTrue(report_dict["ok"])
        self.assertEqual(report_dict["scanned_files"], 5)
        self.assertEqual(report_dict["accepted_files"], 5)
        self.assertEqual(report_dict["rejected_files"], 0)
        self.assertEqual(report_dict["total_size_bytes"], payload_size * 5)
        self.assertEqual(report_dict["summary"]["accepted_files"], 5)
        self.assertEqual(report_dict["metadata"]["inventory_source"], "metadata_only")
        self.assertEqual(validation, [])

        datasets = report_dict["datasets"]
        self.assertEqual([item["relative_path"] for item in datasets], expected_paths)
        self.assertEqual([item["path"] for item in datasets], expected_paths)
        self.assertTrue(all("\\" not in item["relative_path"] for item in datasets))
        self.assertEqual(
            [item["suffix"] for item in datasets],
            [".csv", ".json", ".json.gz", ".feather", ".parquet"],
        )

        diff_dict = diff.to_dict()
        self.assertEqual(
            [item["relative_path"] for item in diff.added_datasets],
            ["alpha.csv", "nested/gamma.json.gz", "prices/epsilon.parquet"],
        )
        self.assertEqual(
            [item["relative_path"] for item in diff.removed_datasets],
            ["removed/omega.csv", "zeta.csv"],
        )
        self.assertEqual(
            [item["relative_path"] for item in diff.changed_datasets],
            ["nested/beta.json", "prices/delta.feather"],
        )
        self.assertEqual(diff_dict["metadata"]["old_dataset_count"], 4)
        self.assertEqual(diff_dict["metadata"]["new_dataset_count"], 5)

        self.assertIn("Offline Data Preflight Summary", summary)
        self.assertIn("datasets:", summary)
        self.assertIn("Offline Data Preflight Diff Summary", diff_summary)
        self.assertEqual(workflow["report_dict"], report_dict)
        self.assertEqual(workflow["stdout_text"], workflow["json_text"])
        self.assertFalse(workflow["metadata"]["wrote_output"])
        self.assertTrue(backtest_gate["ok"])
        self.assertFalse(backtest_gate["metadata"]["real_backtest_executed"])
        self.assertTrue(release_audit["ok"])
        self.assertEqual(release_audit["metadata"]["real_data_scanned"], False)

        rendered = "\n".join(
            [
                report_json,
                json.dumps(report_dict, sort_keys=True),
                json.dumps(validation, sort_keys=True),
                diff.to_json(),
                json.dumps(diff_dict, sort_keys=True),
                summary,
                diff_summary,
                json.dumps(workflow, sort_keys=True),
                json.dumps(backtest_gate, sort_keys=True),
                json.dumps(release_audit, sort_keys=True),
            ]
        )
        self.assertNotIn(PAYLOAD, rendered)


if __name__ == "__main__":
    unittest.main()

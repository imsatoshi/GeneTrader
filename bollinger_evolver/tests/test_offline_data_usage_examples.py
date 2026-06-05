"""Executable usage examples for offline data metadata-only APIs."""

from __future__ import annotations

import builtins
import io
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_backtest_gate import run_backtest_offline_data_gate
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_data_summary import (
    format_offline_data_diff_summary,
    format_offline_data_preflight_summary,
)
from bollinger_evolver.offline_preflight_cli import EXIT_OK, run_offline_data_preflight_cli
from bollinger_evolver.offline_release import run_offline_data_release_readiness_audit
from bollinger_evolver.offline_workflow import run_offline_data_workflow_preflight
from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    run_offline_data_preflight,
)


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataUsageExamples(unittest.TestCase):
    def _write_fake_data(self, root: Path, names: tuple[str, ...] = ("BTC_USDT-1h.csv",)) -> set[Path]:
        files: set[Path] = set()
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PAYLOAD, encoding="utf-8")
            files.add(path.resolve())
        return files

    @contextmanager
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

        with patch.object(Path, "read_text", guarded_read_text):
            with patch.object(Path, "read_bytes", guarded_read_bytes):
                with patch.object(builtins, "open", guarded_open):
                    yield

    def _run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def _assert_payload_absent(self, value: object) -> None:
        self.assertNotIn(PAYLOAD, json.dumps(value, sort_keys=True) if not isinstance(value, str) else value)

    def test_example_1_build_offline_data_preflight_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root, ("BTC_USDT-1h.csv", "ETH_USDT-5m.json"))
            with self._guard_fake_reads(data_files):
                report = build_offline_data_preflight_report(root)
                again = build_offline_data_preflight_report(root)

        report_dict = report.to_dict()
        report_json = report.to_json()
        self.assertEqual(report_json, again.to_json())
        self.assertEqual(report_dict, again.to_dict())
        self.assertTrue(json.loads(report_json)["ok"])
        self.assertEqual(report_dict["accepted_files"], 2)
        self._assert_payload_absent(report_dict)
        self._assert_payload_absent(report_json)

    def test_example_2_run_offline_data_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                result = run_offline_data_preflight(root)

        self.assertTrue(result["ok"])
        self.assertIn("inventory", result)
        self.assertIn("manifest", result)
        self.assertIn("gate", result)
        self.assertIn("report", result)
        self.assertEqual(result["report"]["accepted_files"], 1)
        self._assert_payload_absent(result)

    def test_example_3_run_offline_data_workflow_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            before = {path.relative_to(root).as_posix() for path in root.rglob("*")}
            with self._guard_fake_reads(data_files):
                result = run_offline_data_workflow_preflight(root)
                again = run_offline_data_workflow_preflight(root)
            after = {path.relative_to(root).as_posix() for path in root.rglob("*")}

        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertEqual(result, again)
        self.assertTrue(result["report_dict"]["ok"])
        self.assertFalse(result["metadata"]["wrote_output"])
        self.assertEqual(before, after)
        self._assert_payload_absent(result)

    def test_example_4_run_backtest_offline_data_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                result = run_backtest_offline_data_gate(root)
                again = run_backtest_offline_data_gate(root)

        self.assertTrue(result["ok"])
        self.assertEqual(result, again)
        self.assertEqual(result["gate_summary"]["accepted_files"], 1)
        self.assertTrue(result["metadata"]["metadata_only"])
        self.assertFalse(result["metadata"]["real_backtest_executed"])
        self._assert_payload_absent(result)

    def test_example_5_compare_offline_data_preflight_reports(self) -> None:
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old_root = Path(old_dir)
            new_root = Path(new_dir)
            data_files = self._write_fake_data(old_root)
            data_files.update(self._write_fake_data(new_root, ("BTC_USDT-1h.csv", "ETH_USDT-5m.json")))
            with self._guard_fake_reads(data_files):
                old_report = build_offline_data_preflight_report(old_root)
                new_report = build_offline_data_preflight_report(new_root)
                diff = compare_offline_data_preflight_reports(old_report, new_report)
                again = compare_offline_data_preflight_reports(old_report, new_report)

        self.assertEqual(diff.to_json(), again.to_json())
        self.assertEqual([item["relative_path"] for item in diff.added_datasets], ["ETH_USDT-5m.json"])
        self._assert_payload_absent(diff.to_dict())
        self._assert_payload_absent(diff.to_json())

    def test_example_6_format_offline_data_preflight_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                report = build_offline_data_preflight_report(root)
                summary = format_offline_data_preflight_summary(report)
                again = format_offline_data_preflight_summary(report)

        self.assertIsInstance(summary, str)
        self.assertEqual(summary, again)
        self.assertIn("Offline Data Preflight Summary", summary)
        self._assert_payload_absent(summary)

    def test_example_7_format_offline_data_diff_summary(self) -> None:
        old = {"datasets": [], "summary": {"scanned_files": 0, "accepted_files": 0}}
        new = {
            "datasets": [{"relative_path": "BTC_USDT-1h.csv", "size_bytes": 1, "suffix": ".csv"}],
            "summary": {"scanned_files": 1, "accepted_files": 1},
        }
        diff = compare_offline_data_preflight_reports(old, new)
        summary = format_offline_data_diff_summary(diff)
        again = format_offline_data_diff_summary(diff)

        self.assertEqual(summary, again)
        self.assertIn("added_datasets: 1", summary)
        self._assert_payload_absent(summary)

    def test_example_8_run_offline_data_release_readiness_audit(self) -> None:
        audit = run_offline_data_release_readiness_audit()
        again = run_offline_data_release_readiness_audit()

        self.assertTrue(audit["ok"])
        self.assertEqual(audit, again)
        self.assertTrue(json.dumps(audit, sort_keys=True))
        self.assertFalse(audit["metadata"]["real_data_scanned"])

    def test_example_9_run_offline_data_preflight_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                json_run = self._run_cli(["--root", str(root), "--json"])
                json_run_again = self._run_cli(["--root", str(root), "--json"])
                pretty_run = self._run_cli(["--root", str(root), "--pretty"])
                pretty_run_again = self._run_cli(["--root", str(root), "--pretty"])

        self.assertEqual(json_run[0], EXIT_OK)
        self.assertEqual(pretty_run[0], EXIT_OK)
        self.assertEqual(json_run, json_run_again)
        self.assertEqual(pretty_run, pretty_run_again)
        self.assertTrue(json.loads(json_run[1])["ok"])
        self.assertTrue(json.loads(pretty_run[1])["ok"])
        self._assert_payload_absent(json_run)
        self._assert_payload_absent(pretty_run)


if __name__ == "__main__":
    unittest.main()

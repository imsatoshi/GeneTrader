"""Regression guards for default no-runtime-write offline data flows."""

from __future__ import annotations

import builtins
import io
import json
import os
import shutil
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
WRITE_MODES = ("w", "a", "x")


class WriteMonitor:
    def __init__(self, repo_root: Path, allowed_paths: set[Path] | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.allowed_paths = {path.resolve() for path in (allowed_paths or set())}
        self.records: list[dict[str, object]] = []

    def _path(self, value: object) -> Path | None:
        try:
            return Path(value).resolve()
        except (TypeError, OSError):
            return None

    def _is_repo_path(self, path: Path) -> bool:
        try:
            path.relative_to(self.repo_root)
            return True
        except ValueError:
            return False

    def _record(self, operation: str, path: Path | None) -> None:
        if path is None:
            return
        allowed = path in self.allowed_paths
        self.records.append({"operation": operation, "path": str(path), "allowed": allowed})
        if self._is_repo_path(path) and not allowed:
            raise AssertionError(f"unexpected repository write: {operation} {path}")

    @property
    def blocked_records(self) -> list[dict[str, object]]:
        return [record for record in self.records if not record["allowed"]]


class TestOfflineDataNoRuntimeWrites(unittest.TestCase):
    repo_root = Path(__file__).resolve().parents[2]

    def _write_fake_data(self, root: Path, names: tuple[str, ...] = ("BTC_USDT-1h.csv",)) -> set[Path]:
        files: set[Path] = set()
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PAYLOAD, encoding="utf-8")
            files.add(path.resolve())
        return files

    @contextmanager
    def _monitor_writes(self, allowed_paths: set[Path] | None = None):
        monitor = WriteMonitor(self.repo_root, allowed_paths)
        original_write_text = Path.write_text
        original_write_bytes = Path.write_bytes
        original_open = builtins.open
        original_mkdir = Path.mkdir
        original_touch = Path.touch
        original_unlink = Path.unlink
        original_os_remove = os.remove
        original_shutil_rmtree = shutil.rmtree

        def monitored_write_text(path: Path, *args, **kwargs):
            monitor._record("Path.write_text", path.resolve())
            return original_write_text(path, *args, **kwargs)

        def monitored_write_bytes(path: Path, *args, **kwargs):
            monitor._record("Path.write_bytes", path.resolve())
            return original_write_bytes(path, *args, **kwargs)

        def monitored_open(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in WRITE_MODES):
                monitor._record("builtins.open", monitor._path(file))
            return original_open(file, mode, *args, **kwargs)

        def monitored_mkdir(path: Path, *args, **kwargs):
            monitor._record("Path.mkdir", path.resolve())
            return original_mkdir(path, *args, **kwargs)

        def monitored_touch(path: Path, *args, **kwargs):
            monitor._record("Path.touch", path.resolve())
            return original_touch(path, *args, **kwargs)

        def monitored_unlink(path: Path, *args, **kwargs):
            monitor._record("Path.unlink", path.resolve())
            return original_unlink(path, *args, **kwargs)

        def monitored_remove(path, *args, **kwargs):
            monitor._record("os.remove", monitor._path(path))
            return original_os_remove(path, *args, **kwargs)

        def monitored_rmtree(path, *args, **kwargs):
            monitor._record("shutil.rmtree", monitor._path(path))
            return original_shutil_rmtree(path, *args, **kwargs)

        with patch.object(Path, "write_text", monitored_write_text):
            with patch.object(Path, "write_bytes", monitored_write_bytes):
                with patch.object(builtins, "open", monitored_open):
                    with patch.object(Path, "mkdir", monitored_mkdir):
                        with patch.object(Path, "touch", monitored_touch):
                            with patch.object(Path, "unlink", monitored_unlink):
                                with patch.object(os, "remove", monitored_remove):
                                    with patch.object(shutil, "rmtree", monitored_rmtree):
                                        yield monitor

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
            if "r" in str(mode):
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

    def _assert_no_payload(self, value: object) -> None:
        rendered = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        self.assertNotIn(PAYLOAD, rendered)

    def test_default_python_entries_do_not_write_repository_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root, ("BTC_USDT-1h.csv", "ETH_USDT-5m.json"))
            with self._guard_fake_reads(data_files):
                with self._monitor_writes() as monitor:
                    report = build_offline_data_preflight_report(root)
                    preflight = run_offline_data_preflight(root)
                    workflow = run_offline_data_workflow_preflight(root)
                    gate = run_backtest_offline_data_gate(root)
                    diff = compare_offline_data_preflight_reports({"datasets": []}, report)
                    summary = format_offline_data_preflight_summary(report)
                    diff_summary = format_offline_data_diff_summary(diff)
                    release_audit = run_offline_data_release_readiness_audit()

        self.assertEqual(monitor.records, [])
        self.assertTrue(report.ok)
        self.assertTrue(preflight["ok"])
        self.assertEqual(workflow["exit_code"], EXIT_OK)
        self.assertTrue(gate["ok"])
        self.assertTrue(release_audit["ok"])
        self._assert_no_payload(report.to_dict())
        self._assert_no_payload(preflight)
        self._assert_no_payload(workflow)
        self._assert_no_payload(gate)
        self._assert_no_payload(diff.to_dict())
        self._assert_no_payload(summary)
        self._assert_no_payload(diff_summary)
        self._assert_no_payload(release_audit)

    def test_default_cli_entries_do_not_write_repository_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                with self._monitor_writes() as monitor:
                    json_run = self._run_cli(["--root", str(root), "--json"])
                    pretty_run = self._run_cli(["--root", str(root), "--pretty"])
                    summary_run = self._run_cli(["--root", str(root), "--summary"])

        self.assertEqual(monitor.records, [])
        self.assertEqual(json_run[0], EXIT_OK)
        self.assertEqual(pretty_run[0], EXIT_OK)
        self.assertEqual(summary_run[0], EXIT_OK)
        self._assert_no_payload(json_run)
        self._assert_no_payload(pretty_run)
        self._assert_no_payload(summary_run)

    def test_cli_output_only_writes_explicit_tempfile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "data"
            root.mkdir()
            output = temp / "report.json"
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                with self._monitor_writes({output}) as monitor:
                    result = self._run_cli(["--root", str(root), "--json", "--output", str(output)])

        self.assertEqual(result[0], EXIT_OK)
        self.assertEqual(monitor.records, [{"operation": "Path.write_text", "path": str(output), "allowed": True}])
        self._assert_no_payload(result)

    def test_workflow_output_only_writes_explicit_tempfile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "data"
            root.mkdir()
            output = temp / "workflow-report.json"
            data_files = self._write_fake_data(root)
            with self._guard_fake_reads(data_files):
                with self._monitor_writes({output}) as monitor:
                    result = run_offline_data_workflow_preflight(root, output=output)

        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertEqual(monitor.records, [{"operation": "Path.write_text", "path": str(output), "allowed": True}])
        self.assertTrue(result["metadata"]["wrote_output"])
        self._assert_no_payload(result)

    def test_deterministic_default_outputs_remain_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_files = self._write_fake_data(root, ("BTC_USDT-1h.csv", "ETH_USDT-5m.json"))
            with self._guard_fake_reads(data_files):
                with self._monitor_writes():
                    first_report = build_offline_data_preflight_report(root)
                    second_report = build_offline_data_preflight_report(root)
                    first_summary = format_offline_data_preflight_summary(first_report)
                    second_summary = format_offline_data_preflight_summary(second_report)
                    first_workflow = run_offline_data_workflow_preflight(root)
                    second_workflow = run_offline_data_workflow_preflight(root)
                    first_audit = run_offline_data_release_readiness_audit()
                    second_audit = run_offline_data_release_readiness_audit()

        self.assertEqual(first_report.to_json(), second_report.to_json())
        self.assertEqual(first_report.to_dict(), second_report.to_dict())
        self.assertEqual(first_summary, second_summary)
        self.assertEqual(first_workflow, second_workflow)
        self.assertEqual(first_audit, second_audit)


if __name__ == "__main__":
    unittest.main()

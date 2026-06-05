"""Tests for offline preflight CLI diff mode."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_preflight_cli import (
    EXIT_OK,
    EXIT_USAGE_ERROR,
    run_offline_data_preflight_cli,
)
from bollinger_evolver.preflight import build_offline_data_preflight_report


class TestOfflineDataPreflightCliDiff(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def _report_file(self, root: Path, output: Path) -> None:
        output.write_text(build_offline_data_preflight_report(root).to_json(), encoding="utf-8")

    def test_two_report_json_diff_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_root = base / "old"
            new_root = base / "new"
            old_root.mkdir()
            new_root.mkdir()
            self._write(old_root, "BTC_USDT-1h.json")
            self._write(new_root, "BTC_USDT-1h.json")
            old_report = base / "old.json"
            new_report = base / "new.json"
            self._report_file(old_root, old_report)
            self._report_file(new_root, new_report)
            code, stdout, stderr = self._run(
                ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
            )

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_added_removed_changed_output_is_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_root = base / "old"
            new_root = base / "new"
            old_root.mkdir()
            new_root.mkdir()
            self._write(old_root, "BTC_USDT-1h.json", b"x")
            self._write(old_root, "OLD_USDT-1h.json", b"x")
            self._write(new_root, "BTC_USDT-1h.json", b"xx")
            self._write(new_root, "NEW_USDT-1h.json", b"x")
            old_report = base / "old.json"
            new_report = base / "new.json"
            self._report_file(old_root, old_report)
            self._report_file(new_root, new_report)
            code, stdout, _stderr = self._run(
                ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
            )

        payload = json.loads(stdout)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(payload["added_datasets"][0]["relative_path"], "NEW_USDT-1h.json")
        self.assertEqual(payload["removed_datasets"][0]["relative_path"], "OLD_USDT-1h.json")
        self.assertEqual(payload["changed_datasets"][0]["relative_path"], "BTC_USDT-1h.json")

    def test_diff_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_root = base / "old"
            new_root = base / "new"
            old_root.mkdir()
            new_root.mkdir()
            self._write(old_root, "z/ETH_USDT-5m.csv")
            self._write(new_root, "a/BTC_USDT-1h.json")
            old_report = base / "old.json"
            new_report = base / "new.json"
            self._report_file(old_root, old_report)
            self._report_file(new_root, new_report)
            first = self._run(["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-pretty"])
            second = self._run(["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-pretty"])

        self.assertEqual(first[1], second[1])

    def test_invalid_old_path_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            new_report = base / "new.json"
            new_report.write_text("{}", encoding="utf-8")
            code, stdout, stderr = self._run(
                ["--diff-old", str(base / "missing.json"), "--diff-new", str(new_report), "--diff-json"]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("diff_old_not_found", stderr)

    def test_invalid_json_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_report = base / "old.json"
            new_report = base / "new.json"
            old_report.write_text("{", encoding="utf-8")
            new_report.write_text("{}", encoding="utf-8")
            code, _stdout, stderr = self._run(
                ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertIn("diff_failed", stderr)

    def test_output_writes_tempfile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_report = base / "old.json"
            new_report = base / "new.json"
            output = base / "diff.json"
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            new_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            code, stdout, stderr = self._run(
                [
                    "--diff-old",
                    str(old_report),
                    "--diff-new",
                    str(new_report),
                    "--diff-json",
                    "--output",
                    str(output),
                    "--quiet",
                ]
            )
            written = output.read_text(encoding="utf-8")

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(written)["ok"])

    def test_diff_mode_does_not_scan_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_report = base / "old.json"
            new_report = base / "new.json"
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            new_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            with patch(
                "bollinger_evolver.offline_preflight_cli.build_offline_data_preflight_report",
                side_effect=AssertionError("root scan should not run"),
            ):
                code, _stdout, _stderr = self._run(
                    ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
                )

        self.assertEqual(code, EXIT_OK)

    def test_secret_payload_does_not_leak(self) -> None:
        marker = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            old_report = base / "old.json"
            new_report = base / "new.json"
            old_report.write_text(
                json.dumps(
                    {
                        "datasets": [
                            {
                                "relative_path": "BTC_USDT-1h.json",
                                "size_bytes": 1,
                                "suffix": ".json",
                                "file_type": "json",
                                "content": marker,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            new_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            code, stdout, stderr = self._run(
                ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
            )

        self.assertEqual(code, EXIT_OK)
        self.assertNotIn(marker, stdout)
        self.assertNotIn(marker, stderr)

    def test_diff_mode_only_reads_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            data_file = base / "BTC_USDT-1h.csv"
            data_file.write_text("SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR", encoding="utf-8")
            old_report = base / "old.json"
            new_report = base / "new.json"
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            new_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            original_read_text = Path.read_text

            def guarded_read_text(path: Path, *args, **kwargs):
                if path == data_file:
                    raise AssertionError("data file should not be read")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", guarded_read_text):
                code, stdout, stderr = self._run(
                    ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
                )

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_regular_preflight_cli_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(["--root", str(root), "--json"])

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])


if __name__ == "__main__":
    unittest.main()

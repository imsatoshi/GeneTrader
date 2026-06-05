"""Regression guard for metadata-only offline data flows."""

from __future__ import annotations

import builtins
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.data_gate import run_inventory_manifest_gate
from bollinger_evolver.data_manifest import build_manifest_from_inventory
from bollinger_evolver.offline_data import inventory_offline_data
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_preflight_cli import run_offline_data_preflight_cli
from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    run_offline_data_preflight,
)


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataMetadataOnlyRegression(unittest.TestCase):
    def _build_tree(self, root: Path) -> None:
        for name in ("a.csv", "b.json", "c.json.gz", "d.feather", "e.parquet"):
            (root / name).write_text(PAYLOAD, encoding="utf-8")

    def _run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_all_offline_entries_do_not_leak_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            self._build_tree(root)

            inventory = inventory_offline_data(root)
            manifest = build_manifest_from_inventory(inventory)
            gate = run_inventory_manifest_gate(manifest)
            preflight = run_offline_data_preflight(root)
            report = build_offline_data_preflight_report(root)
            cli_json = self._run_cli(["--root", str(root), "--json"])
            cli_pretty = self._run_cli(["--root", str(root), "--pretty"])
            output = Path(temp_dir) / "report.json"
            cli_output = self._run_cli(["--root", str(root), "--json", "--output", str(output)])
            output_text = output.read_text(encoding="utf-8")
            diff = compare_offline_data_preflight_reports({"datasets": []}, report)
            old_report = Path(temp_dir) / "old_report.json"
            new_report = Path(temp_dir) / "new_report.json"
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            new_report.write_text(report.to_json(), encoding="utf-8")
            cli_diff = self._run_cli(
                ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
            )

        rendered = "\n".join(
            [
                str(inventory),
                str(manifest),
                str(gate),
                str(preflight),
                str(report.to_dict()),
                report.to_json(),
                cli_json[1],
                cli_json[2],
                cli_pretty[1],
                cli_pretty[2],
                cli_output[1],
                cli_output[2],
                output_text,
                diff.to_json(),
                cli_diff[1],
                cli_diff[2],
            ]
        )
        self.assertNotIn(PAYLOAD, rendered)

    def test_metadata_only_paths_do_not_read_fake_data_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            self._build_tree(root)
            data_files = {path.resolve() for path in root.iterdir()}
            old_report = Path(temp_dir) / "old_report.json"
            new_report = Path(temp_dir) / "new_report.json"
            report = build_offline_data_preflight_report(root)
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
            new_report.write_text(report.to_json(), encoding="utf-8")
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
                    except TypeError:
                        pass
                return original_open(file, mode, *args, **kwargs)

            with patch.object(Path, "read_text", guarded_read_text):
                with patch.object(Path, "read_bytes", guarded_read_bytes):
                    with patch.object(builtins, "open", guarded_open):
                        inventory = inventory_offline_data(root)
                        manifest = build_manifest_from_inventory(inventory)
                        gate = run_inventory_manifest_gate(manifest)
                        preflight = run_offline_data_preflight(root)
                        report = build_offline_data_preflight_report(root)
                        cli_json = self._run_cli(["--root", str(root), "--json"])
                        cli_pretty = self._run_cli(["--root", str(root), "--pretty"])
                        output = Path(temp_dir) / "report_out.json"
                        cli_output = self._run_cli(
                            ["--root", str(root), "--json", "--output", str(output)]
                        )
                        diff = compare_offline_data_preflight_reports({"datasets": []}, report)
                        cli_diff = self._run_cli(
                            [
                                "--diff-old",
                                str(old_report),
                                "--diff-new",
                                str(new_report),
                                "--diff-json",
                            ]
                        )

        self.assertEqual(inventory["files"][0]["size_bytes"], len(PAYLOAD))
        self.assertTrue(manifest["datasets"])
        self.assertIn("ok", gate)
        self.assertIn("report", preflight)
        self.assertTrue(report.to_json())
        self.assertTrue(cli_json[1])
        self.assertTrue(cli_pretty[1])
        self.assertTrue(cli_output[1])
        self.assertTrue(diff.to_json())
        self.assertTrue(cli_diff[1])

    def test_outputs_are_deterministic_and_import_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._build_tree(root)
            first = build_offline_data_preflight_report(root).to_json()
            second = build_offline_data_preflight_report(root).to_json()

        import bollinger_evolver

        self.assertEqual(first, second)
        self.assertTrue(callable(bollinger_evolver.inventory_offline_data))


if __name__ == "__main__":
    unittest.main()

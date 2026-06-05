"""Tests for explicit offline data metadata-only boundaries."""

from __future__ import annotations

import builtins
import importlib
import io
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.data_gate import run_inventory_manifest_gate
from bollinger_evolver.data_manifest import build_manifest_from_inventory
from bollinger_evolver.offline_data import inventory_offline_data
from bollinger_evolver.offline_data_boundary import (
    get_legacy_content_read_allowlist,
    get_offline_data_metadata_only_boundary,
    run_offline_data_boundary_audit,
)
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_preflight_cli import run_offline_data_preflight_cli
from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    run_offline_data_preflight,
)


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataBoundary(unittest.TestCase):
    def _write_fake_data(self, root: Path) -> Path:
        path = root / "BTC_USDT-1h.csv"
        path.write_text(PAYLOAD, encoding="utf-8")
        return path

    def _run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_boundary_audit_returns_ok_with_known_legacy_warning(self) -> None:
        audit = run_offline_data_boundary_audit()

        self.assertTrue(audit["ok"])
        self.assertEqual(audit["issues"], [])
        self.assertTrue(audit["metadata_only_apis"])
        self.assertTrue(audit["legacy_content_read_apis"])
        self.assertIn(
            {
                "classification": "KNOWN_LEGACY_ALLOWED_READ",
                "code": "known_legacy_content_read_paths",
                "count": len(audit["legacy_content_read_apis"]),
            },
            audit["warnings"],
        )

    def test_metadata_only_boundary_is_deterministic_json(self) -> None:
        first = get_offline_data_metadata_only_boundary()
        second = get_offline_data_metadata_only_boundary()

        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_legacy_allowlist_is_deterministic_json(self) -> None:
        first = get_legacy_content_read_allowlist()
        second = get_legacy_content_read_allowlist()

        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_metadata_only_apis_are_importable_and_callable(self) -> None:
        boundary = get_offline_data_metadata_only_boundary()
        for item in boundary["metadata_only_apis"]:
            with self.subTest(api=item["name"]):
                value = importlib.import_module(item["module"])
                for part in item["qualname"].split("."):
                    value = getattr(value, part)
                self.assertTrue(callable(value))

    def test_import_bollinger_evolver_does_not_trigger_boundary_scan(self) -> None:
        import bollinger_evolver

        with patch.object(Path, "rglob", side_effect=AssertionError("unexpected scan")):
            reloaded = importlib.reload(bollinger_evolver)

        self.assertTrue(callable(reloaded.run_offline_data_boundary_audit))

    def test_boundary_audit_does_not_read_fake_market_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_file = self._write_fake_data(Path(temp_dir)).resolve()
            original_read_text = Path.read_text
            original_read_bytes = Path.read_bytes
            original_open = builtins.open

            def guarded_read_text(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_text(path, *args, **kwargs)

            def guarded_read_bytes(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_bytes(path, *args, **kwargs)

            def guarded_open(file, mode="r", *args, **kwargs):
                if "r" in mode:
                    try:
                        if Path(file).resolve() == fake_file:
                            raise AssertionError("fake market content read")
                    except TypeError:
                        pass
                return original_open(file, mode, *args, **kwargs)

            with patch.object(Path, "read_text", guarded_read_text):
                with patch.object(Path, "read_bytes", guarded_read_bytes):
                    with patch.object(builtins, "open", guarded_open):
                        audit = run_offline_data_boundary_audit()

        rendered = json.dumps(audit, sort_keys=True)
        self.assertTrue(audit["ok"])
        self.assertNotIn(PAYLOAD, rendered)

    def test_metadata_path_survives_legacy_content_readers_disabled(self) -> None:
        import bollinger_evolver.data_gate as data_gate
        import bollinger_evolver.data_manifest as data_manifest

        legacy_targets = [
            (data_gate, "_inspect_file_schema"),
            (data_gate, "_read_csv_columns"),
            (data_gate, "_read_first_json_row"),
            (data_gate, "_read_first_jsonl_row"),
            (data_gate, "_read_pandas_columns"),
            (data_gate, "run_offline_data_gate"),
            (data_manifest, "_parse_csv_file"),
            (data_manifest, "_parse_json_file"),
            (data_manifest, "_parse_jsonl_file"),
            (data_manifest, "_parse_pandas_file"),
            (data_manifest, "build_offline_data_manifest"),
            (data_manifest, "parse_candles_from_file"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            self._write_fake_data(root)
            old_report = Path(temp_dir) / "old.json"
            new_report = Path(temp_dir) / "new.json"

            with ExitStack() as stack:
                for module, name in legacy_targets:
                    stack.enter_context(
                        patch.object(
                            module,
                            name,
                            side_effect=AssertionError(f"legacy reader called: {name}"),
                        )
                    )

                inventory = inventory_offline_data(root)
                manifest = build_manifest_from_inventory(inventory)
                gate = run_inventory_manifest_gate(manifest)
                preflight = run_offline_data_preflight(root)
                report = build_offline_data_preflight_report(root)
                cli = self._run_cli(["--root", str(root), "--json"])
                old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")
                new_report.write_text(report.to_json(), encoding="utf-8")
                diff = compare_offline_data_preflight_reports({"datasets": []}, report)
                cli_diff = self._run_cli(
                    ["--diff-old", str(old_report), "--diff-new", str(new_report), "--diff-json"]
                )

        self.assertTrue(inventory["files"])
        self.assertTrue(manifest["datasets"])
        self.assertTrue(gate["ok"])
        self.assertTrue(preflight["ok"])
        self.assertTrue(report.ok)
        self.assertEqual(cli[0], 0)
        self.assertTrue(diff.ok)
        self.assertEqual(cli_diff[0], 0)
        self.assertNotIn(PAYLOAD, cli[1])
        self.assertNotIn(PAYLOAD, cli_diff[1])


if __name__ == "__main__":
    unittest.main()

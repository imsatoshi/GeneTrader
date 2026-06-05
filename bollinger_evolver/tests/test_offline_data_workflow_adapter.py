"""Tests for workflow-friendly offline data preflight adapter."""

from __future__ import annotations

import builtins
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_preflight_cli import (
    EXIT_OK,
    EXIT_PREFLIGHT_FAILED,
    EXIT_USAGE_ERROR,
)
from bollinger_evolver.offline_workflow import run_offline_data_workflow_preflight


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataWorkflowAdapter(unittest.TestCase):
    def _write(self, root: Path, name: str, content: str = PAYLOAD) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_workflow_preflight_returns_zero_for_fake_temp_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before = {path.relative_to(root).as_posix() for path in root.rglob("*")}
            self._write(root, "BTC_USDT-1h.csv")
            result = run_offline_data_workflow_preflight(root)
            after = {path.relative_to(root).as_posix() for path in root.rglob("*")}

        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertTrue(result["report_dict"]["ok"])
        self.assertEqual(result["stderr_text"], "")
        self.assertEqual(result["stdout_text"], result["json_text"])
        self.assertEqual(after - before, {"BTC_USDT-1h.csv"})

    def test_workflow_preflight_output_is_explicit_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "data"
            root.mkdir()
            output = temp / "report.json"
            self._write(root, "BTC_USDT-1h.csv")
            result = run_offline_data_workflow_preflight(root, output=output)
            written = output.read_text(encoding="utf-8")

        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertTrue(result["metadata"]["wrote_output"])
        self.assertEqual(written, result["json_text"])

    def test_workflow_preflight_fail_on_warning_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            self._write(root, "README.txt")
            result = run_offline_data_workflow_preflight(root, fail_on_warning=True)

        self.assertEqual(result["exit_code"], EXIT_PREFLIGHT_FAILED)
        self.assertTrue(result["report_dict"]["ok"])
        self.assertTrue(result["report_dict"]["warnings"])

    def test_workflow_preflight_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            first = run_offline_data_workflow_preflight(root)
            second = run_offline_data_workflow_preflight(root)

        self.assertEqual(first["json_text"], second["json_text"])
        self.assertEqual(json.loads(first["json_text"]), json.loads(second["json_text"]))

    def test_workflow_preflight_payload_guard_and_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_file = self._write(root, "BTC_USDT-1h.csv").resolve()
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
                        result = run_offline_data_workflow_preflight(root)

        rendered = json.dumps(result, sort_keys=True)
        self.assertEqual(result["exit_code"], EXIT_OK)
        self.assertNotIn(PAYLOAD, rendered)

    def test_workflow_preflight_missing_root_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_workflow_preflight(Path(temp_dir) / "missing")

        self.assertEqual(result["exit_code"], EXIT_USAGE_ERROR)
        self.assertEqual(result["stdout_text"], "")
        self.assertIn("root_not_found", result["stderr_text"])


if __name__ == "__main__":
    unittest.main()

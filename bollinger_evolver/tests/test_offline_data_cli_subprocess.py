"""Subprocess integration tests for the offline preflight CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.offline_preflight_cli import EXIT_OK, EXIT_USAGE_ERROR


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataCliSubprocess(unittest.TestCase):
    def _write(self, root: Path, name: str, content: str = PAYLOAD) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "bollinger_evolver.offline_preflight_cli", *args],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_subprocess_preflight_json_pretty_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "data"
            root.mkdir()
            output = temp / "report.json"
            self._write(root, "BTC_USDT-1h.csv")

            json_run = self._run(["--root", str(root), "--json"])
            pretty_run = self._run(["--root", str(root), "--pretty"])
            output_run = self._run(["--root", str(root), "--json", "--output", str(output)])
            written = output.read_text(encoding="utf-8")

        self.assertEqual(json_run.returncode, EXIT_OK)
        self.assertEqual(pretty_run.returncode, EXIT_OK)
        self.assertEqual(output_run.returncode, EXIT_OK)
        self.assertTrue(json.loads(json_run.stdout)["ok"])
        self.assertTrue(json.loads(pretty_run.stdout)["ok"])
        self.assertTrue(json.loads(written)["ok"])
        combined = json_run.stdout + json_run.stderr + pretty_run.stdout + output_run.stdout + written
        self.assertNotIn(PAYLOAD, combined)

    def test_subprocess_diff_json_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "data"
            root.mkdir()
            self._write(root, "BTC_USDT-1h.csv")
            old_report = temp / "old.json"
            new_report = temp / "new.json"
            diff_output = temp / "diff.json"
            old_report.write_text(json.dumps({"datasets": []}), encoding="utf-8")

            make_report = self._run(["--root", str(root), "--json", "--output", str(new_report)])
            diff_run = self._run(
                [
                    "--diff-old",
                    str(old_report),
                    "--diff-new",
                    str(new_report),
                    "--diff-json",
                    "--output",
                    str(diff_output),
                ]
            )
            written = diff_output.read_text(encoding="utf-8")

        self.assertEqual(make_report.returncode, EXIT_OK)
        self.assertEqual(diff_run.returncode, EXIT_OK)
        self.assertTrue(json.loads(diff_run.stdout)["ok"])
        self.assertTrue(json.loads(written)["ok"])
        self.assertNotIn(PAYLOAD, diff_run.stdout + diff_run.stderr + written)

    def test_subprocess_invalid_args_return_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self._run(["--root", str(Path(temp_dir) / "missing"), "--json"])

        self.assertEqual(result.returncode, EXIT_USAGE_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("root_not_found", result.stderr)
        self.assertNotIn(PAYLOAD, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

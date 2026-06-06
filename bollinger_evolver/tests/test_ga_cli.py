"""Tests for the mock GA artifact CLI."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver import ga_cli


def _run_cli(args: list[str]) -> str:
    stream = io.StringIO()
    with redirect_stdout(stream):
        exit_code = ga_cli.main(args)
    if exit_code != 0:
        raise AssertionError(f"unexpected exit code: {exit_code}")
    return stream.getvalue()


class TestGACli(unittest.TestCase):
    def test_ga_cli_run_mock_writes_session_summary_to_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mock-session"

            stdout = _run_cli(
                [
                    "run-mock",
                    "--generations",
                    "2",
                    "--population-size",
                    "4",
                    "--seed",
                    "42",
                    "--output",
                    str(output),
                ]
            )
            summary = json.loads((output / "session_summary.json").read_text(encoding="utf-8"))

        self.assertIn("session_summary", json.loads(stdout))
        self.assertEqual(summary["schema_version"], "ga-session-summary/v1")
        self.assertEqual(summary["generation"], 2)

    def test_ga_cli_run_mock_writes_generation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mock-session"

            _run_cli(
                [
                    "run-mock",
                    "--generations",
                    "3",
                    "--population-size",
                    "4",
                    "--seed",
                    "7",
                    "--output",
                    str(output),
                ]
            )

            files = sorted(path.name for path in output.glob("generation_*.json"))

        self.assertEqual(files, ["generation_001.json", "generation_002.json", "generation_003.json"])

    def test_ga_cli_rejects_missing_output_dir(self) -> None:
        with self.assertRaises(SystemExit):
            ga_cli.main(["run-mock", "--generations", "1"])

    def test_ga_cli_rejects_disallowed_output_dir(self) -> None:
        with self.assertRaises(SystemExit):
            ga_cli.main(["run-mock", "--output", str(ga_cli._repo_root() / ".runtime" / "ga")])
        with self.assertRaises(SystemExit):
            ga_cli.main(["run-mock", "--output", str(ga_cli._repo_root() / "user_data" / "data" / "ga")])
        with self.assertRaises(SystemExit):
            ga_cli.main(["run-mock", "--output", str(ga_cli._repo_root())])

    def test_ga_cli_does_not_use_real_backtest_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "mock-session"
            with patch("bollinger_evolver.ga_cli.MockBacktestAdapter") as mock_adapter:
                from bollinger_evolver.backtest_adapter import MockBacktestAdapter

                mock_adapter.side_effect = MockBacktestAdapter

                stdout = _run_cli(["run-mock", "--generations", "1", "--population-size", "4", "--output", str(output)])

        self.assertTrue(mock_adapter.called)
        self.assertEqual(json.loads(stdout)["adapter"], "MockBacktestAdapter")


if __name__ == "__main__":
    unittest.main()

"""Tests for safe mock risk report CLI."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver import risk_cli


def _run_cli(args: list[str]) -> str:
    stream = io.StringIO()
    with redirect_stdout(stream):
        exit_code = risk_cli.main(args)
    if exit_code != 0:
        raise AssertionError(f"unexpected exit code: {exit_code}")
    return stream.getvalue()


class TestRiskCli(unittest.TestCase):
    def test_risk_cli_explain_writes_reports_to_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "risk"

            stdout = _run_cli(["explain", "--fixture", "safe_default", "--output", str(output)])
            risk_report = json.loads((output / "risk_report.json").read_text(encoding="utf-8"))
            explanation = json.loads((output / "strategy_explanation.json").read_text(encoding="utf-8"))

        self.assertIn("risk_report", json.loads(stdout))
        self.assertEqual(risk_report["schema_version"], "mock-risk-report/v1")
        self.assertEqual(explanation["schema_version"], "strategy-explainability/v1")

    def test_risk_cli_rejects_missing_output_dir(self) -> None:
        with self.assertRaises(SystemExit):
            risk_cli.main(["explain", "--fixture", "safe_default"])

    def test_risk_cli_rejects_disallowed_output_dir(self) -> None:
        root = risk_cli._repo_root()

        with self.assertRaises(SystemExit):
            risk_cli.main(["explain", "--fixture", "safe_default", "--output", str(root)])
        with self.assertRaises(SystemExit):
            risk_cli.main(["explain", "--fixture", "safe_default", "--output", str(root / ".runtime" / "risk")])
        with self.assertRaises(SystemExit):
            risk_cli.main(["explain", "--fixture", "safe_default", "--output", str(root / "user_data" / "data" / "risk")])

    def test_risk_cli_does_not_execute_external_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("subprocess.run", side_effect=AssertionError("external process should not run")):
                _run_cli(["explain", "--fixture", "safe_default", "--output", str(Path(tmp) / "risk")])

    def test_risk_cli_high_risk_fixture_contains_warnings(self) -> None:
        report, explanation = risk_cli.build_fixture_risk_report("high_leverage_high_drawdown")

        self.assertIn("high_leverage_strategy", explanation["warnings"])
        self.assertIn("risk_governor:reduced_risk_after_drawdown", report["warnings"])
        json.dumps(report, sort_keys=True)


if __name__ == "__main__":
    unittest.main()

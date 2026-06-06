"""Tests for the fail-closed real Freqtrade execution gate."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from bollinger_evolver.execution_gate import validate_real_backtest_execution_gate


class TestExecutionGate(unittest.TestCase):
    def test_execution_gate_fails_without_env(self) -> None:
        result = validate_real_backtest_execution_gate(
            {"dry_run_only": True, "output_root": "tmp-output"},
            approval={"execution_allowed": True},
            env={},
        )

        self.assertFalse(result["ok"])
        self.assertIn("real_freqtrade_backtest_env_not_enabled", result["errors"])

    def test_execution_gate_fails_without_approval(self) -> None:
        result = validate_real_backtest_execution_gate(
            {"dry_run_only": True, "output_root": "tmp-output"},
            env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
        )

        self.assertFalse(result["ok"])
        self.assertIn("explicit_approval_required", result["errors"])

    def test_execution_gate_fails_when_not_dry_run_only(self) -> None:
        result = validate_real_backtest_execution_gate(
            {"dry_run_only": False, "output_root": "tmp-output"},
            approval={"execution_allowed": True},
            env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
        )

        self.assertFalse(result["ok"])
        self.assertIn("dry_run_only_required", result["errors"])

    def test_execution_gate_rejects_forbidden_commands(self) -> None:
        for command in ("trade", "live", "hyperopt", "download-data"):
            with self.subTest(command=command):
                result = validate_real_backtest_execution_gate(
                    {"dry_run_only": True, "output_root": "tmp-output", "command": f"freqtrade {command}"},
                    approval={"execution_allowed": True},
                    env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
                )

                self.assertFalse(result["ok"])
                self.assertIn("forbidden_freqtrade_command", result["errors"])

    def test_execution_gate_rejects_secret_like_fields(self) -> None:
        result = validate_real_backtest_execution_gate(
            {
                "dry_run_only": True,
                "output_root": "tmp-output",
                "strategy_config": {"api_key": "do-not-keep"},
            },
            approval={"execution_allowed": True},
            env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
        )

        self.assertFalse(result["ok"])
        self.assertIn("secret_like_request_field_not_allowed", result["errors"])

    def test_execution_gate_result_is_json_serializable(self) -> None:
        result = validate_real_backtest_execution_gate()

        json.dumps(result, sort_keys=True)
        self.assertFalse(result["ok"])

    def test_execution_gate_rejects_repo_runtime_and_data_output_roots(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        for output_root in (
            repo_root,
            repo_root / ".runtime" / "freqtrade-out",
            repo_root / "user_data" / "data" / "freqtrade-out",
        ):
            with self.subTest(output_root=str(output_root)):
                result = validate_real_backtest_execution_gate(
                    {"dry_run_only": True, "output_root": str(output_root)},
                    approval={"execution_allowed": True},
                    env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
                )

                self.assertFalse(result["ok"])
                self.assertIn("disallowed_output_root", result["errors"])


if __name__ == "__main__":
    unittest.main()

"""Tests for human-readable session report rendering."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.ga.session_report import (
    contains_sensitive_fields,
    redact_sensitive_fields,
    render_session_report,
)


def _session_summary(**overrides: object) -> dict:
    summary = {
        "session_id": "report-session",
        "status": "PASS",
        "mock_evaluation": True,
        "real_backtest": False,
        "allow_real_backtest": False,
        "mock_first": True,
        "completed": 2,
        "generations_requested": 2,
        "population_size": 4,
        "dataQualityGateDisabled": False,
        "dataQualityGate": {
            "status": "PASS",
            "allowed_for_evaluation": True,
            "fail_reasons": [],
            "warnings": [],
        },
        "generation_summaries": [
            {
                "best_fitness_score": 10.0,
                "success_count": 4,
                "failure_count": 0,
                "individuals": [],
            },
            {
                "best_fitness_score": 12.5,
                "success_count": 3,
                "failure_count": 1,
                "individuals": [{"reason": "data_quality_gate_failed"}],
            },
        ],
        "final_best": {
            "individual_id": "gen001_ind002",
            "fitness": 12.5,
            "genes_hash": "abc123",
            "strategy_name": "BollingerResonance_Gen001_Ind002",
            "strategy_path": "user_data/strategies/generated/BollingerResonance_Gen001_Ind002.py",
            "metrics": {"profit_total": 1.2, "total_trades": 24},
            "genes": {"bb_period_15m": 20},
        },
    }
    summary.update(overrides)
    return summary


class TestSessionReport(unittest.TestCase):
    def test_render_without_writing_returns_report_payload(self) -> None:
        result = render_session_report(_session_summary(), Path("."), write_files=False)

        self.assertTrue(result["success"])
        self.assertIsNone(result["report_json_path"])
        self.assertIsNone(result["report_markdown_path"])
        self.assertEqual(result["report"]["recommendation"]["status"], "READY_FOR_REVIEW")
        self.assertIn("# Bollinger Evolver Session Report", result["markdown"])
        self.assertIn("## Safety Boundary", result["markdown"])

    def test_render_writes_json_and_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = render_session_report(_session_summary(), temp_dir, write_files=True)
            report_json_path = Path(result["report_json_path"])
            report_markdown_path = Path(result["report_markdown_path"])

            self.assertTrue(report_json_path.exists())
            self.assertTrue(report_markdown_path.exists())
            self.assertIn('"version": "runner-session-report-v1"', report_json_path.read_text(encoding="utf-8"))
            self.assertIn("## Final Best Individual", report_markdown_path.read_text(encoding="utf-8"))

    def test_blocked_data_quality_session_marks_blocked_recommendation(self) -> None:
        summary = _session_summary(
            status="BLOCKED",
            completed=0,
            dataQualityGate={
                "status": "BLOCKED",
                "allowed_for_evaluation": False,
                "fail_reasons": ["missing_pair_timeframe_entry"],
                "warnings": [],
            },
            generation_summaries=[],
            final_best=None,
            reason="data_quality_gate_failed",
        )

        result = render_session_report(summary, Path("."), write_files=False)

        self.assertEqual(result["report"]["recommendation"]["status"], "BLOCKED_BY_DATA_QA")
        self.assertIn("missing_pair_timeframe_entry", result["markdown"])

    def test_missing_final_best_marks_no_final_best(self) -> None:
        summary = _session_summary(final_best=None, reason="all_candidates_failed")

        result = render_session_report(summary, Path("."), write_files=False)

        self.assertEqual(result["report"]["recommendation"]["status"], "NO_FINAL_BEST")
        self.assertIn("No final best individual.", result["markdown"])

    def test_sensitive_fields_are_redacted_from_report(self) -> None:
        summary = _session_summary(api_key="top-secret", final_best={"secret": "do-not-keep"})

        self.assertTrue(contains_sensitive_fields(summary))
        redacted = redact_sensitive_fields(summary)
        self.assertFalse(contains_sensitive_fields(redacted))

        result = render_session_report(summary, Path("."), write_files=False)

        self.assertTrue(result["report"]["riskAndSafety"]["contains_sensitive_fields"])
        self.assertNotIn("top-secret", result["markdown"])
        self.assertNotIn("do-not-keep", str(result["report"]))


if __name__ == "__main__":
    unittest.main()

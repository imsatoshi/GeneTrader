"""Tests for Pareto frontier selection."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.pareto import select_pareto_frontier


def _candidate(**overrides):
    data = {
        "candidate_id": "a",
        "profit": 0.20,
        "sharpe": 1.40,
        "stability_score": 0.80,
        "max_drawdown": 0.10,
        "leverage": 2.0,
        "risk_per_trade": 0.01,
    }
    data.update(overrides)
    return data


class TestParetoFrontier(unittest.TestCase):
    def test_pareto_removes_dominated_candidate(self) -> None:
        result = select_pareto_frontier(
            [
                _candidate(candidate_id="strong", profit=0.30, max_drawdown=0.07, leverage=1.5),
                _candidate(candidate_id="weak", profit=0.20, max_drawdown=0.10, leverage=2.0),
            ]
        )

        self.assertEqual([item["candidate_id"] for item in result], ["strong"])

    def test_pareto_keeps_non_dominated_candidate(self) -> None:
        result = select_pareto_frontier(
            [
                _candidate(candidate_id="high-profit", profit=0.35, max_drawdown=0.16),
                _candidate(candidate_id="low-drawdown", profit=0.20, max_drawdown=0.05),
            ]
        )

        self.assertEqual([item["candidate_id"] for item in result], ["high-profit", "low-drawdown"])

    def test_pareto_output_order_is_stable(self) -> None:
        result = select_pareto_frontier(
            [
                _candidate(candidate_id="a", profit=0.30, max_drawdown=0.12),
                _candidate(candidate_id="b", profit=0.25, max_drawdown=0.06),
                _candidate(candidate_id="c", profit=0.32, max_drawdown=0.14),
            ]
        )

        self.assertEqual([item["candidate_id"] for item in result], ["a", "b", "c"])

    def test_pareto_output_is_json_serializable(self) -> None:
        result = select_pareto_frontier([_candidate()])

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("candidate_id", encoded)

    def test_pareto_missing_objective_fails_clearly(self) -> None:
        candidate = _candidate()
        candidate.pop("stability_score")

        with self.assertRaisesRegex(ValueError, "candidate_missing_objective:stability_score"):
            select_pareto_frontier([candidate])


if __name__ == "__main__":
    unittest.main()

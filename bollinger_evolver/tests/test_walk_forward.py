"""Tests for mock walk-forward evaluation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.walk_forward import (
    WalkForwardConfig,
    calculate_stability_score,
    run_mock_walk_forward_evaluation,
)


GENOME = {
    "genome_id": "walk-forward",
    "bb_window": 24,
    "bb_stddev": 2.1,
    "stop_loss_pct": 0.03,
    "take_profit_pct": 0.08,
    "leverage": 1.5,
    "risk_per_trade": 0.01,
}


class TestWalkForward(unittest.TestCase):
    def test_walk_forward_returns_train_validation_test(self) -> None:
        result = run_mock_walk_forward_evaluation(GENOME, config=WalkForwardConfig(base_seed=10, trade_count=20))

        self.assertIn("train", result)
        self.assertIn("validation", result)
        self.assertIn("test", result)
        self.assertIn("stability_score", result)

    def test_walk_forward_is_deterministic(self) -> None:
        config = WalkForwardConfig(base_seed=22, trade_count=25)

        first = run_mock_walk_forward_evaluation(GENOME, config=config)
        second = run_mock_walk_forward_evaluation(GENOME, config=config)

        self.assertEqual(first, second)

    def test_stability_score_penalizes_metric_drift(self) -> None:
        stable = [
            {"profit": 0.10, "sharpe": 1.0, "win_rate": 0.55, "max_drawdown": 0.05},
            {"profit": 0.11, "sharpe": 1.02, "win_rate": 0.56, "max_drawdown": 0.06},
            {"profit": 0.10, "sharpe": 1.01, "win_rate": 0.55, "max_drawdown": 0.05},
        ]
        drifting = [
            {"profit": 0.20, "sharpe": 2.0, "win_rate": 0.75, "max_drawdown": 0.02},
            {"profit": -0.05, "sharpe": -0.2, "win_rate": 0.42, "max_drawdown": 0.18},
            {"profit": 0.02, "sharpe": 0.1, "win_rate": 0.44, "max_drawdown": 0.15},
        ]

        self.assertGreater(calculate_stability_score(stable), calculate_stability_score(drifting))

    def test_walk_forward_result_is_json_serializable(self) -> None:
        result = run_mock_walk_forward_evaluation(GENOME, config=WalkForwardConfig(base_seed=31, trade_count=20))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("mock-walk-forward/v1", encoded)
        self.assertGreaterEqual(result["stability_score"], 0.0)
        self.assertLessEqual(result["stability_score"], 1.0)


if __name__ == "__main__":
    unittest.main()

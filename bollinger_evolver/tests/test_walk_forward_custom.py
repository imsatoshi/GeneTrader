"""Tests for custom walk-forward evaluation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.walk_forward_custom import CustomWalkForwardConfig, evaluate_custom_walk_forward


class TestCustomWalkForward(unittest.TestCase):
    def test_custom_walk_forward_returns_segments_and_penalty_components(self) -> None:
        result = evaluate_custom_walk_forward(
            CustomStrategyGenome(genome_id="wf-custom"),
            config=CustomWalkForwardConfig(base_seed=5, trade_count=20),
        )

        self.assertIn("train", result["walk_forward"])
        self.assertIn("validation", result["walk_forward"])
        self.assertIn("test", result["walk_forward"])
        self.assertIn("overfit_penalty", result["fitness_components"])

    def test_custom_walk_forward_is_json_serializable(self) -> None:
        result = evaluate_custom_walk_forward(CustomStrategyGenome(genome_id="wf-json"))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("custom-walk-forward/v1", encoded)


if __name__ == "__main__":
    unittest.main()

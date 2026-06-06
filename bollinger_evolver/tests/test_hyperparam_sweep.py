"""Tests for custom strategy hyperparameter sweep."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.hyperparam_sweep import HyperparamSweepConfig, run_custom_hyperparam_sweep


SWEEP_SPACE = {
    "entry_bb_window": [18, 20],
    "entry_bb_stddev": [1.8, 2.0],
    "leverage": [1.0, 2.0],
}


class TestHyperparamSweep(unittest.TestCase):
    def test_grid_sweep_generates_expected_combinations(self) -> None:
        result = run_custom_hyperparam_sweep(
            SWEEP_SPACE,
            config=HyperparamSweepConfig(mode="grid", max_samples=20, trade_count=20),
        )

        self.assertEqual(result["run_count"], 8)

    def test_random_sweep_is_deterministic_with_seed(self) -> None:
        config = HyperparamSweepConfig(mode="random", seed=9, max_samples=5, trade_count=20)

        first = run_custom_hyperparam_sweep(SWEEP_SPACE, config=config)
        second = run_custom_hyperparam_sweep(SWEEP_SPACE, config=config)

        self.assertEqual(first["runs"], second["runs"])

    def test_sweep_rejects_unknown_parameter(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown_sweep_parameters"):
            run_custom_hyperparam_sweep({"unknown": [1]})

    def test_sweep_respects_max_samples(self) -> None:
        result = run_custom_hyperparam_sweep(
            SWEEP_SPACE,
            config=HyperparamSweepConfig(mode="grid", max_samples=3, trade_count=20),
        )

        self.assertEqual(result["run_count"], 3)

    def test_sweep_does_not_mutate_base_genome(self) -> None:
        base = CustomStrategyGenome(genome_id="base", leverage=3.0)
        before = base.to_dict()

        result = run_custom_hyperparam_sweep(
            {"leverage": [1.0, 2.0]},
            base_genome=base,
            config=HyperparamSweepConfig(max_samples=2, trade_count=20),
        )

        self.assertFalse(result["base_genome_mutated"])
        self.assertEqual(base.to_dict(), before)

    def test_sweep_result_is_json_serializable(self) -> None:
        result = run_custom_hyperparam_sweep(
            SWEEP_SPACE,
            config=HyperparamSweepConfig(max_samples=2, trade_count=20),
        )

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("custom-hyperparam-sweep/v1", encoded)

    def test_sweep_best_run_has_highest_fitness(self) -> None:
        result = run_custom_hyperparam_sweep(
            SWEEP_SPACE,
            config=HyperparamSweepConfig(max_samples=8, trade_count=20),
        )

        best = max(item["fitness"] for item in result["runs"])
        self.assertEqual(result["best_run"]["fitness"], best)


if __name__ == "__main__":
    unittest.main()

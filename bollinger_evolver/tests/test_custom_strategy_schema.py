"""Tests for the custom strategy schema skeleton."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace

from bollinger_evolver.custom_strategy_schema import (
    CUSTOM_STRATEGY_PARAMETER_NAMES,
    CustomStrategyBounds,
    CustomStrategyGenome,
    custom_strategy_config_from_genome,
    validate_custom_strategy_genome,
)
from bollinger_evolver.risk_governor import RiskGovernorConfig, apply_risk_governor


class TestCustomStrategySchema(unittest.TestCase):
    def _genome(self, **overrides) -> CustomStrategyGenome:
        data = {"genome_id": "custom-001"}
        data.update(overrides)
        return CustomStrategyGenome(**data)

    def test_custom_strategy_bounds_cover_all_parameters(self) -> None:
        bounds = CustomStrategyBounds().to_dict()

        self.assertEqual(set(CUSTOM_STRATEGY_PARAMETER_NAMES), set(bounds))
        self.assertEqual(len(CUSTOM_STRATEGY_PARAMETER_NAMES), 14)

    def test_validate_custom_strategy_genome_accepts_default_genome(self) -> None:
        validate_custom_strategy_genome(self._genome())

    def test_validate_custom_strategy_genome_rejects_missing_field(self) -> None:
        data = self._genome().to_dict()
        data.pop("entry_bb_window")

        with self.assertRaisesRegex(ValueError, "missing"):
            validate_custom_strategy_genome(data)

    def test_validate_custom_strategy_genome_rejects_unknown_field(self) -> None:
        data = self._genome().to_dict()
        data["unknown"] = 1

        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_custom_strategy_genome(data)

    def test_validate_custom_strategy_genome_rejects_out_of_bounds(self) -> None:
        with self.assertRaisesRegex(ValueError, "leverage_out_of_bounds"):
            validate_custom_strategy_genome(self._genome(leverage=99.0))

    def test_validate_custom_strategy_genome_requires_int_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "entry_bb_window_must_be_int"):
            validate_custom_strategy_genome(self._genome(entry_bb_window=20.5))

    def test_custom_strategy_config_from_genome_is_json_safe(self) -> None:
        config = custom_strategy_config_from_genome(self._genome(leverage=2.0, risk_per_trade=0.015))

        encoded = json.dumps(config, sort_keys=True)
        self.assertIn("custom-strategy/v1", encoded)
        self.assertEqual(config["entry"]["bollinger_window"], 20)
        self.assertFalse(config["execution_controls"]["real_execution_enabled"])
        self.assertTrue(config["constraints"]["no_exchange_api"])

    def test_custom_strategy_config_exposes_risk_governor_fields(self) -> None:
        config = custom_strategy_config_from_genome(self._genome(leverage=6.0, risk_per_trade=0.04))

        advice = apply_risk_governor(
            config,
            {"drawdown": 0.14, "max_consecutive_losses": 5},
            config=RiskGovernorConfig(max_leverage=3.0, max_risk_per_trade=0.02),
        )

        self.assertEqual(advice["adjusted_leverage"], 3.0)
        self.assertLessEqual(advice["adjusted_risk_per_trade"], 0.01)
        self.assertEqual(config["leverage"], 6.0)

    def test_custom_strategy_genome_is_not_mutated_by_mapping(self) -> None:
        genome = self._genome(leverage=2.0)
        before = genome.to_dict()

        custom_strategy_config_from_genome(genome)

        self.assertEqual(genome.to_dict(), before)
        self.assertEqual(replace(genome, leverage=2.0), genome)


if __name__ == "__main__":
    unittest.main()

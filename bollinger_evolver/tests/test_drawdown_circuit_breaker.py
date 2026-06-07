"""Tests for mock drawdown circuit breaker simulation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.drawdown_circuit_breaker import (
    DrawdownCircuitBreakerConfig,
    simulate_drawdown_circuit_breaker,
)


class TestDrawdownCircuitBreaker(unittest.TestCase):
    def test_drawdown_reduce_risk_trigger(self) -> None:
        result = simulate_drawdown_circuit_breaker(
            [100.0, 110.0, 98.0],
            config=DrawdownCircuitBreakerConfig(reduce_risk_drawdown=0.08, pause_trading_drawdown=0.20),
        )

        self.assertTrue(result["triggered"])
        self.assertEqual(result["action"], "reduce_risk")
        self.assertEqual(result["trigger_index"], 2)

    def test_drawdown_pause_trading_trigger(self) -> None:
        result = simulate_drawdown_circuit_breaker(
            [100.0, 120.0, 80.0],
            config=DrawdownCircuitBreakerConfig(reduce_risk_drawdown=0.08, pause_trading_drawdown=0.20),
        )

        self.assertTrue(result["triggered"])
        self.assertEqual(result["action"], "pause_trading")

    def test_drawdown_no_trigger_when_curve_is_stable(self) -> None:
        result = simulate_drawdown_circuit_breaker([100.0, 105.0, 107.0])

        self.assertFalse(result["triggered"])
        self.assertIsNone(result["trigger_index"])
        self.assertEqual(result["action"], "none")

    def test_drawdown_output_is_json_serializable(self) -> None:
        result = simulate_drawdown_circuit_breaker([100.0, 90.0])

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("drawdown-circuit-breaker/v1", encoded)


if __name__ == "__main__":
    unittest.main()

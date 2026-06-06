"""Tests for parsing Freqtrade backtest JSON payloads."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.backtest_adapter import NormalizedBacktestResult
from bollinger_evolver.freqtrade_result_parser import parse_freqtrade_result_payload


def _payload(**overrides):
    payload = {
        "profit_total": 0.12,
        "max_drawdown": 0.08,
        "sharpe": 1.4,
        "winrate": 0.57,
        "total_trades": 40,
        "max_consecutive_losses": 3,
        "leverage": 1.0,
        "risk_per_trade": 0.01,
    }
    payload.update(overrides)
    return payload


class TestFreqtradeResultParser(unittest.TestCase):
    def test_parse_minimal_valid_freqtrade_result(self) -> None:
        result = parse_freqtrade_result_payload(_payload())

        self.assertEqual(result.profit, 0.12)
        self.assertEqual(result.max_drawdown, 0.08)
        self.assertEqual(result.total_trades, 40)
        self.assertEqual(result.max_consecutive_losses, 3)

    def test_parse_rejects_missing_profit(self) -> None:
        payload = _payload()
        payload.pop("profit_total")

        with self.assertRaises(ValueError):
            parse_freqtrade_result_payload(payload)

    def test_parse_rejects_missing_drawdown(self) -> None:
        payload = _payload()
        payload.pop("max_drawdown")

        with self.assertRaises(ValueError):
            parse_freqtrade_result_payload(payload)

    def test_parse_rejects_non_numeric_metric(self) -> None:
        with self.assertRaises(ValueError):
            parse_freqtrade_result_payload(_payload(sharpe="not-a-number"))

    def test_parser_returns_normalized_backtest_result(self) -> None:
        result = parse_freqtrade_result_payload({"strategy": {"BollingerBandStrategy": _payload()}})

        self.assertIsInstance(result, NormalizedBacktestResult)
        self.assertEqual(result.metadata["strategy_name"], "BollingerBandStrategy")

    def test_parser_output_is_json_serializable(self) -> None:
        result = parse_freqtrade_result_payload(_payload(winrate=57.0))

        encoded = json.dumps(result.to_dict(), sort_keys=True)
        self.assertIn("freqtrade_result_parser", encoded)
        self.assertEqual(result.win_rate, 0.57)


if __name__ == "__main__":
    unittest.main()

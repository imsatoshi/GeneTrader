"""Tests for Bollinger Evolver data coverage safety gate."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.data_quality import evaluate_data_coverage_gate


def _manifest(**entry_overrides: object) -> dict:
    entry = {
        "pair": "BTC/USDT",
        "timeframe": "15m",
        "status": "ready",
        "row_count": 500,
        "gap_count": 0,
        "invalid_ohlc_count": 0,
    }
    entry.update(entry_overrides)
    return {
        "status": "ready",
        "pairs": ["BTC/USDT"],
        "timeframes": ["15m"],
        "expected_file_count": 1,
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": int(entry.get("invalid_ohlc_count", 0) or 0),
        "gap_count": int(entry.get("gap_count", 0) or 0),
        "entries": [entry],
    }


class TestDataQualityGate(unittest.TestCase):
    def test_missing_manifest_blocks_evaluation(self) -> None:
        gate = evaluate_data_coverage_gate(
            None,
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
        )

        self.assertEqual(gate["status"], "MISSING")
        self.assertFalse(gate["allowed_for_evaluation"])
        self.assertIn("data_quality_manifest_missing", gate["fail_reasons"])

    def test_missing_required_timeframe_fails(self) -> None:
        gate = evaluate_data_coverage_gate(
            _manifest(),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m", "1h"],
        )

        self.assertEqual(gate["status"], "FAIL")
        self.assertFalse(gate["allowed_for_evaluation"])
        self.assertIn("missing_pair_timeframe", gate["fail_reasons"])

    def test_low_candle_count_fails(self) -> None:
        gate = evaluate_data_coverage_gate(
            _manifest(row_count=20),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
            min_candles_per_pair_timeframe=100,
        )

        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("low_candle_count", gate["fail_reasons"])

    def test_invalid_ohlc_fails_by_default(self) -> None:
        gate = evaluate_data_coverage_gate(
            _manifest(invalid_ohlc_count=1),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
        )

        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("invalid_ohlc", gate["fail_reasons"])

    def test_gap_ratio_fails_by_default(self) -> None:
        gate = evaluate_data_coverage_gate(
            _manifest(row_count=100, gap_count=3),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
            max_gap_ratio=0.02,
        )

        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("excessive_gap_ratio", gate["fail_reasons"])

    def test_ready_manifest_passes(self) -> None:
        gate = evaluate_data_coverage_gate(
            _manifest(),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
        )

        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(gate["allowed_for_evaluation"])
        self.assertEqual(gate["fail_reasons"], [])

    def test_sensitive_fields_do_not_enter_gate_payload(self) -> None:
        manifest = _manifest(api_secret="hidden-secret")

        gate = evaluate_data_coverage_gate(
            manifest,
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
        )

        self.assertNotIn("hidden-secret", json.dumps(gate, sort_keys=True))


if __name__ == "__main__":
    unittest.main()

"""Tests for deriving offline data requirements from GA config payloads."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.config_requirements import (
    build_offline_requirements_from_config,
    load_offline_requirements_from_config,
)


class TestConfigRequirements(unittest.TestCase):
    def test_build_requirements_from_config_pairs_and_timeframes(self) -> None:
        result = build_offline_requirements_from_config(
            {
                "pairs": ["eth-usdt", "BTC/USDT"],
                "base_timeframe": "15M",
                "informative_timeframes": ["1H", "4h"],
            }
        )

        self.assertEqual(result["pairs"], ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(result["timeframes"], ["15m", "1h", "4h"])

    def test_build_requirements_from_config_single_timeframe(self) -> None:
        result = build_offline_requirements_from_config(
            {"market_filter_pair": "BTC/USDT", "base_timeframe": "15m"}
        )

        self.assertEqual(result, {"pairs": ["BTC/USDT"], "timeframes": ["15m"]})

    def test_build_requirements_rejects_missing_pairs(self) -> None:
        with self.assertRaisesRegex(ValueError, "config_pairs_missing"):
            build_offline_requirements_from_config({"base_timeframe": "15m"})

    def test_build_requirements_rejects_missing_timeframes(self) -> None:
        with self.assertRaisesRegex(ValueError, "config_timeframes_missing"):
            build_offline_requirements_from_config({"pairs": ["BTC/USDT"]})

    def test_build_requirements_normalizes_pairs_and_timeframes(self) -> None:
        result = build_offline_requirements_from_config(
            {"pair_whitelist": ["btc_usdt"], "base_timeframe": "1H", "informative_timeframes": ["4H"]}
        )

        self.assertEqual(result["pairs"], ["BTC/USDT"])
        self.assertEqual(result["timeframes"], ["1h", "4h"])

    def test_load_requirements_from_config_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(
                json.dumps({"market_filter_pair": "BTC/USDT", "base_timeframe": "15m"}),
                encoding="utf-8",
            )
            result = load_offline_requirements_from_config(path)

        self.assertEqual(result, {"pairs": ["BTC/USDT"], "timeframes": ["15m"]})


if __name__ == "__main__":
    unittest.main()

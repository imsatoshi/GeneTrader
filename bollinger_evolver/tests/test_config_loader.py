"""Unit tests for the standalone Bollinger config loader."""

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.config_loader import (
    BollingerConfigError,
    REQUIRED_FIELDS,
    load_bollinger_config,
    validate_bollinger_config,
)


def _valid_config() -> dict:
    return {
        "base_timeframe": "15m",
        "informative_timeframes": ["1h", "4h"],
        "market_filter_pair": "BTC/USDT",
        "population_size": 30,
        "generations": 20,
        "crossover_prob": 0.8,
        "mutation_prob": 0.2,
        "pool_processes": 4,
        "enable_walk_forward": True,
        "walk_forward_train_weeks": 26,
        "walk_forward_test_weeks": 4,
        "min_trades_per_week": 0.5,
        "max_drawdown_limit": 0.35,
        "min_profit_factor": 1.1,
        "random_seed": 42,
    }


class TestValidateBollingerConfig(unittest.TestCase):
    def test_accepts_valid_config(self) -> None:
        config = _valid_config()
        validated = validate_bollinger_config(config)
        self.assertEqual(validated["base_timeframe"], "15m")

    def test_missing_required_field_raises(self) -> None:
        config = _valid_config()
        config.pop("population_size")

        with self.assertRaises(BollingerConfigError):
            validate_bollinger_config(config)

    def test_invalid_timeframes_raises(self) -> None:
        config = _valid_config()
        config["informative_timeframes"] = []

        with self.assertRaises(BollingerConfigError):
            validate_bollinger_config(config)


class TestLoadBollingerConfig(unittest.TestCase):
    def test_loads_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps(_valid_config()), encoding="utf-8")

            loaded = load_bollinger_config(config_path)

        self.assertEqual(loaded["market_filter_pair"], "BTC/USDT")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(BollingerConfigError):
            load_bollinger_config("missing-config.json")

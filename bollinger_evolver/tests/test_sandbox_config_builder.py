"""Tests for safe sandbox Freqtrade config construction."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.freqtrade_adapter import REDACTED, build_sandbox_config


class TestSandboxConfigBuilder(unittest.TestCase):
    def test_sandbox_config_redacts_exchange_keys(self) -> None:
        config = build_sandbox_config(
            {
                "dry_run": True,
                "exchange": {
                    "name": "binance",
                    "api_key": "key",
                    "api_secret": "secret",
                    "password": "pass",
                },
                "telegram": {"token": "telegram-token"},
                "webhook": {"webhook_url": "https://example.invalid/hook"},
            }
        )

        self.assertEqual(config["exchange"]["api_key"], REDACTED)
        self.assertEqual(config["exchange"]["api_secret"], REDACTED)
        self.assertEqual(config["telegram"]["token"], REDACTED)
        self.assertEqual(config["webhook"]["webhook_url"], REDACTED)
        self.assertNotIn("telegram-token", json.dumps(config, sort_keys=True))

    def test_sandbox_config_forces_dry_run(self) -> None:
        config = build_sandbox_config({"exchange": {"name": "binance"}})

        self.assertTrue(config["dry_run"])

    def test_sandbox_config_rejects_live_mode(self) -> None:
        for payload in (
            {"dry_run": False},
            {"live_mode": True},
            {"trading_mode": "live"},
            {"trading_mode": "production"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    build_sandbox_config(payload)

    def test_sandbox_config_is_json_serializable(self) -> None:
        config = build_sandbox_config({"dry_run": True, "exchange": {"name": "binance"}})

        json.dumps(config, sort_keys=True)


if __name__ == "__main__":
    unittest.main()

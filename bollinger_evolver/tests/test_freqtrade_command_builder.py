"""Tests for safe Freqtrade command spec construction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.freqtrade_adapter import (
    FreqtradeAdapterRequest,
    build_freqtrade_command_spec,
)


def _request(root: Path, **overrides) -> FreqtradeAdapterRequest:
    data = {
        "strategy_config": {"bb_window": 20},
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "timerange": "20240101-20240201",
        "run_id": "stage-097",
        "dry_run_only": True,
        "output_root": str(root / "out"),
        "approval": {"execution_allowed": True},
    }
    data.update(overrides)
    return FreqtradeAdapterRequest(**data)


class TestFreqtradeCommandBuilder(unittest.TestCase):
    def test_command_builder_returns_list_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = build_freqtrade_command_spec(
                _request(root),
                sandbox_config={"dry_run": True},
                allowed_output_roots=(root,),
            )

        self.assertIsInstance(spec["args"], list)
        self.assertTrue(all(isinstance(arg, str) for arg in spec["args"]))
        self.assertEqual(spec["args"][:2], ["freqtrade", "backtesting"])

    def test_command_builder_sets_shell_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = build_freqtrade_command_spec(
                _request(root),
                sandbox_config={"dry_run": True},
                allowed_output_roots=(root,),
            )

        self.assertFalse(spec["shell"])

    def test_command_builder_rejects_trade_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                build_freqtrade_command_spec(
                    _request(root, command="trade"),
                    sandbox_config={"dry_run": True},
                    allowed_output_roots=(root,),
                )

    def test_command_builder_rejects_hyperopt_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                build_freqtrade_command_spec(
                    _request(root, command="hyperopt"),
                    sandbox_config={"dry_run": True},
                    allowed_output_roots=(root,),
                )

    def test_command_builder_rejects_download_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                build_freqtrade_command_spec(
                    _request(root, command="download-data"),
                    sandbox_config={"dry_run": True},
                    allowed_output_roots=(root,),
                )

    def test_command_builder_rejects_dry_run_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                build_freqtrade_command_spec(
                    _request(root, dry_run_only=False),
                    sandbox_config={"dry_run": True},
                    allowed_output_roots=(root,),
                )

    def test_command_builder_redacts_sensitive_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = build_freqtrade_command_spec(
                _request(root),
                sandbox_config={"dry_run": True},
                allowed_output_roots=(root,),
                env={"PATH": "bin", "API_KEY": "secret-value", "TOKEN": "token-value"},
            )

        self.assertEqual(spec["env"], {"PATH": "bin"})
        self.assertNotIn("API_KEY", spec["env"])

    def test_command_builder_rejects_non_allowlisted_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            with self.assertRaises(ValueError):
                build_freqtrade_command_spec(
                    _request(Path(outside)),
                    sandbox_config={"dry_run": True},
                    allowed_output_roots=(Path(allowed),),
                )


if __name__ == "__main__":
    unittest.main()

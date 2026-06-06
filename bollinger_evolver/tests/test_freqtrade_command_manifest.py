"""Tests for plan-only Freqtrade command manifests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.freqtrade_command_manifest import (
    BacktestCommandPlan,
    BacktestCommandManifest,
    build_backtest_plan_from_genome,
    build_freqtrade_backtest_command_manifest,
    command_manifest_to_json_safe_dict,
    validate_command_plan_paths,
    write_backtest_command_manifest,
)


def _make_plan_root() -> tuple[tempfile.TemporaryDirectory[str], dict[str, Path]]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    userdir = root / "user_data"
    datadir = root / "data"
    strategies = root / "strategies"
    future_results = root / "future_results"
    userdir.mkdir()
    datadir.mkdir()
    strategies.mkdir()
    config = root / "config.json"
    strategy_file = strategies / "BollingerBandStrategy.py"
    config.write_text("{}", encoding="utf-8")
    strategy_file.write_text("class BollingerBandStrategy: pass\n", encoding="utf-8")
    return tmp, {
        "root": root,
        "userdir": userdir,
        "datadir": datadir,
        "strategies": strategies,
        "strategy_file": strategy_file,
        "future_results": future_results,
        "config": config,
    }


class TestFreqtradeCommandManifest(unittest.TestCase):
    def test_basic_manifest_builds_argv(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            manifest = build_freqtrade_backtest_command_manifest(
                BacktestCommandPlan(
                    strategy_name="BollingerBandStrategy",
                    config_path=paths["config"],
                    userdir_path=paths["userdir"],
                    datadir_path=paths["datadir"],
                    strategy_path=paths["strategy_file"],
                    backtest_directory=paths["future_results"],
                    timeframe="5m",
                    timerange="20240101-20240201",
                    pairs=("BTC/USDT",),
                    dry_run_wallet=1000.0,
                    stake_amount=100.0,
                    fee=0.001,
                    max_open_trades=3,
                    enable_protections=True,
                    timeframe_detail="1m",
                    cache="none",
                    allowed_roots=(paths["root"],),
                )
            )

        self.assertIsInstance(manifest, BacktestCommandManifest)
        self.assertEqual(manifest.argv[:4], ("freqtrade", "backtesting", "--strategy", "BollingerBandStrategy"))
        self.assertIn("--backtest-directory", manifest.argv)
        self.assertIn("<redacted:future_results>", manifest.argv)
        self.assertEqual(manifest.execution_mode, "plan_only_no_execution")

    def test_no_execution_safety_flags(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            manifest = build_freqtrade_backtest_command_manifest(
                BacktestCommandPlan(strategy_name="BollingerBandStrategy", allowed_roots=(paths["root"],))
            )

        self.assertFalse(manifest.safety_flags["freqtrade_executed"])
        self.assertFalse(manifest.safety_flags["subprocess_used"])
        self.assertFalse(manifest.safety_flags["shell_used"])
        self.assertFalse(manifest.safety_flags["exchange_api_used"])
        self.assertFalse(manifest.safety_flags["network_used"])
        self.assertFalse(manifest.safety_flags["secrets_loaded"])
        self.assertFalse(manifest.safety_flags["real_backtest_result_created"])

    def test_allowed_roots_required(self) -> None:
        with self.assertRaises(ValueError):
            build_freqtrade_backtest_command_manifest(BacktestCommandPlan(strategy_name="BollingerBandStrategy"))

    def test_rejects_outside_root_paths(self) -> None:
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            root = Path(allowed)
            outside_root = Path(outside)
            config = outside_root / "config.json"
            config.write_text("{}", encoding="utf-8")
            datadir = outside_root / "data"
            strategy_path = outside_root / "strategy.py"
            datadir.mkdir()
            strategy_path.write_text("class S: pass\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                validate_command_plan_paths(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        config_path=config,
                        allowed_roots=(root,),
                    )
                )
            with self.assertRaises(ValueError):
                validate_command_plan_paths(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        datadir_path=datadir,
                        allowed_roots=(root,),
                    )
                )
            with self.assertRaises(ValueError):
                validate_command_plan_paths(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        strategy_path=strategy_path,
                        allowed_roots=(root,),
                    )
                )
            with self.assertRaises(ValueError):
                validate_command_plan_paths(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        backtest_directory=outside_root / "future",
                        allowed_roots=(root,),
                    )
                )

    def test_rejects_unsupported_config_suffix(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            config = paths["root"] / "config.yaml"
            config.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_freqtrade_backtest_command_manifest(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        config_path=config,
                        allowed_roots=(paths["root"],),
                    )
                )

    def test_redacts_absolute_paths(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            manifest = build_freqtrade_backtest_command_manifest(
                BacktestCommandPlan(
                    strategy_name="BollingerBandStrategy",
                    config_path=paths["config"],
                    userdir_path=paths["userdir"],
                    allowed_roots=(paths["root"],),
                )
            )
            encoded = json.dumps(command_manifest_to_json_safe_dict(manifest), sort_keys=True)

        self.assertNotIn(str(paths["root"]), encoded)
        self.assertNotIn("C:/Users", encoded)
        self.assertNotIn("/home/", encoded)
        self.assertIn("<redacted:config.json>", encoded)

    def test_rejects_shell_metacharacters(self) -> None:
        tmp, paths = _make_plan_root()
        bad_plans = [
            BacktestCommandPlan(strategy_name="BadStrategy;rm", allowed_roots=(paths["root"],)),
            BacktestCommandPlan(
                strategy_name="BollingerBandStrategy",
                timerange="20240101-20240201&&bad",
                allowed_roots=(paths["root"],),
            ),
            BacktestCommandPlan(
                strategy_name="BollingerBandStrategy",
                pairs=("BTC/USDT;bad",),
                allowed_roots=(paths["root"],),
            ),
            BacktestCommandPlan(
                strategy_name="BollingerBandStrategy",
                notes="x | y",
                allowed_roots=(paths["root"],),
            ),
        ]
        with tmp:
            for plan in bad_plans:
                with self.subTest(plan=plan):
                    with self.assertRaises(ValueError):
                        build_freqtrade_backtest_command_manifest(plan)

    def test_validates_export_and_cache_enum(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            with self.assertRaises(ValueError):
                build_freqtrade_backtest_command_manifest(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        export="bad",
                        allowed_roots=(paths["root"],),
                    )
                )
            with self.assertRaises(ValueError):
                build_freqtrade_backtest_command_manifest(
                    BacktestCommandPlan(
                        strategy_name="BollingerBandStrategy",
                        cache="bad",
                        allowed_roots=(paths["root"],),
                    )
                )

    def test_json_safe_and_deterministic_manifest(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            plan = BacktestCommandPlan(
                strategy_name="BollingerBandStrategy",
                timeframe="1h",
                pairs=("BTC/USDT", "ETH/USDT"),
                allowed_roots=(paths["root"],),
            )
            first = command_manifest_to_json_safe_dict(build_freqtrade_backtest_command_manifest(plan))
            second = command_manifest_to_json_safe_dict(build_freqtrade_backtest_command_manifest(plan))

        json.dumps(first, sort_keys=True)
        self.assertEqual(first, second)

    def test_genome_bridge_redacts_secret_like_keys(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            plan = build_backtest_plan_from_genome(
                {
                    "bb_window": 20,
                    "api_key": "do-not-keep",
                    "secret": "do-not-keep",
                    "risk_per_trade": 0.01,
                },
                strategy_name="BollingerBandStrategy",
                allowed_roots=(paths["root"],),
            )
            manifest = build_freqtrade_backtest_command_manifest(plan)
            encoded = json.dumps(command_manifest_to_json_safe_dict(manifest), sort_keys=True)

        self.assertIn("genome_hash", encoded)
        self.assertIn("redacted_genome_keys", encoded)
        self.assertNotIn("do-not-keep", encoded)

    def test_write_manifest_artifact_to_explicit_temp_path(self) -> None:
        tmp, paths = _make_plan_root()
        with tmp:
            manifest = build_freqtrade_backtest_command_manifest(
                BacktestCommandPlan(strategy_name="BollingerBandStrategy", allowed_roots=(paths["root"],))
            )
            output_path = paths["root"] / "manifest" / "plan.json"

            written = write_backtest_command_manifest(manifest, output_path)
            loaded = json.loads(written.read_text(encoding="utf-8"))

        self.assertEqual(loaded["execution_mode"], "plan_only_no_execution")
        self.assertFalse(loaded["safety_flags"]["real_backtest_result_created"])


if __name__ == "__main__":
    unittest.main()

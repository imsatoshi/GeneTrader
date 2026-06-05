"""Tests for read-only backtest readiness preflight."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.preflight import (
    _check_backtest_adapter_default_disabled,
    _check_bollinger_strategy_import,
    _check_freqtrade_import,
    _check_runner_cli_rejects_live_args,
    run_backtest_preflight,
)


def _safe_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "dry_run": True,
        "api_key": "CHANGE_ME_API_KEY_PLACEHOLDER",
        "jwt_secret_key": "CHANGE_ME_JWT_SECRET_PLACEHOLDER",
        "password": "CHANGE_ME_PASSWORD_PLACEHOLDER",
    }
    config.update(overrides)
    return config


def _manifest(**entry_overrides: object) -> dict[str, object]:
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
        "entries": [entry],
    }


class TestBacktestPreflight(unittest.TestCase):
    def _write_json(self, root: Path, name: str, payload: dict[str, object]) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_freqtrade_missing_returns_warn_not_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            with patch(
                "bollinger_evolver.preflight._check_freqtrade_import",
                return_value={
                    "id": "check_freqtrade_import",
                    "status": "WARN",
                    "message": "freqtrade_not_installed",
                    "evidence": {},
                },
            ), patch(
                "bollinger_evolver.preflight._check_bollinger_strategy_import",
                return_value={
                    "id": "check_bollinger_strategy_import",
                    "status": "WARN",
                    "message": "strategy_import_blocked_by_missing_freqtrade",
                    "evidence": {},
                },
            ):
                result = run_backtest_preflight(
                    config_path=str(config_path),
                    generated_strategy_dir=str(root / "generated"),
                    output_dir=str(root / "out"),
                    write_report=False,
                )

        self.assertEqual(result["status"], "WARN")
        self.assertFalse(result["readiness"]["freqtrade_available"])
        self.assertFalse(result["readiness"]["strategy_import_ok"])
        self.assertNotIn("freqtrade_not_installed", result["blocked_reasons"])

    def test_strategy_import_helper_warns_when_freqtrade_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            strategy_dir = Path(temp_dir)
            (strategy_dir / "BollingerResonanceStrategy.py").write_text("pass\n", encoding="utf-8")
            with patch(
                "bollinger_evolver.preflight._import_strategy_module",
                side_effect=ModuleNotFoundError("No module named 'freqtrade'"),
            ) as _mock:
                result = _check_bollinger_strategy_import("BollingerResonanceStrategy", strategy_dir)

        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["message"], "strategy_import_blocked_by_missing_freqtrade")

    def test_config_path_missing_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_backtest_preflight(
                config_path=None,
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertEqual(result["status"], "WARN")
        self.assertFalse(result["readiness"]["config_present"])

    def test_config_with_placeholder_secrets_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertNotEqual(result["status"], "BLOCKED")
        self.assertTrue(result["readiness"]["config_safe"])

    def test_config_with_real_looking_secret_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(
                root,
                "config.json",
                _safe_config(api_key="live-secret-value"),
            )
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("config_contains_real_looking_secret", result["blocked_reasons"])

    def test_live_trading_flag_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(
                root,
                "config.json",
                _safe_config(dry_run=False, live_trading=True),
            )
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("config_contains_live_trading_flag", result["blocked_reasons"])

    def test_generated_strategy_dir_probe_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            generated_dir = root / "generated"
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(generated_dir),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertTrue(result["readiness"]["generated_strategy_dir_ok"])
        self.assertFalse(generated_dir.exists())

    def test_missing_data_manifest_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                data_manifest_path=None,
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertEqual(result["status"], "WARN")
        self.assertFalse(result["readiness"]["data_quality_gate_ok"])

    def test_explicit_bad_data_manifest_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            manifest_path = self._write_json(root, "manifest.json", _manifest(row_count=10))
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                data_manifest_path=str(manifest_path),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("data_quality_gate_failed", result["blocked_reasons"])

    def test_good_data_manifest_passes_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            manifest_path = self._write_json(root, "manifest.json", _manifest())
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                data_manifest_path=str(manifest_path),
                output_dir=str(root / "out"),
                write_report=False,
            )

        self.assertTrue(result["readiness"]["data_quality_gate_ok"])

    def test_allow_real_backtest_default_disabled_check_passes(self) -> None:
        check, passed = _check_backtest_adapter_default_disabled()
        self.assertTrue(passed)
        self.assertEqual(check["status"], "PASS")

    def test_runner_cli_rejects_live_and_secret_args(self) -> None:
        check, passed = _check_runner_cli_rejects_live_args()
        self.assertTrue(passed)
        self.assertEqual(check["status"], "PASS")

    def test_write_report_creates_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_json(root, "config.json", _safe_config())
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=True,
            )

            report_path = Path(result["report_path"])
            markdown_path = Path(result["report_markdown_path"])
            self.assertTrue(report_path.exists())
            self.assertTrue(markdown_path.exists())

    def test_reports_do_not_contain_raw_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_secret = "super-secret-live-value"
            config_path = self._write_json(
                root,
                "config.json",
                _safe_config(api_key=raw_secret),
            )
            result = run_backtest_preflight(
                config_path=str(config_path),
                generated_strategy_dir=str(root / "generated"),
                output_dir=str(root / "out"),
                write_report=True,
            )

            report_text = Path(result["report_path"]).read_text(encoding="utf-8")
            markdown_text = Path(result["report_markdown_path"]).read_text(encoding="utf-8")
            serialized = json.dumps(result, sort_keys=True)

        self.assertNotIn(raw_secret, report_text)
        self.assertNotIn(raw_secret, markdown_text)
        self.assertNotIn(raw_secret, serialized)

    def test_freqtrade_helper_warns_when_module_missing(self) -> None:
        with patch(
            "bollinger_evolver.preflight.importlib.import_module",
            side_effect=ModuleNotFoundError("No module named 'freqtrade'"),
        ):
            result = _check_freqtrade_import()

        self.assertEqual(result["status"], "WARN")
        self.assertEqual(result["message"], "freqtrade_not_installed")


if __name__ == "__main__":
    unittest.main()

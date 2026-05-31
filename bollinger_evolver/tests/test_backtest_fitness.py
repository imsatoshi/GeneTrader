"""Tests for the Bollinger backtest fitness evaluator."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.evaluators import (
    FitnessConfig,
    FitnessResult,
    build_backtest_params,
    compute_fitness_score,
    evaluate_candidate,
    normalize_backtest_metrics,
    sanitize_mapping,
    write_evaluation_artifact,
)


def _fitness_config(**overrides: object) -> FitnessConfig:
    base = {
        "strategy": "BollingerResonance_Gen001_Ind001",
        "config_path": "config.json",
        "timerange": "20240101-20240201",
        "timeframe": "15m",
        "pairs": ("BTC/USDT",),
        "result_dir": "results/bollinger_evolver/backtests",
        "timeout_seconds": 120,
        "profit_weight": 1.0,
        "sharpe_weight": 0.25,
        "drawdown_weight": 1.0,
        "winrate_weight": 0.05,
        "trade_count_weight": 0.01,
        "min_trades": 5,
        "max_drawdown_pct": 25.0,
        "failed_score": -1_000_000.0,
    }
    base.update(overrides)
    return FitnessConfig(**base)


def _success_runner(metrics: dict | None = None, **extra: object):
    payload = {
        "success": True,
        "strategy_name": "BollingerResonance_Gen001_Ind001",
        "timerange": "20240101-20240201",
        "timeframe": "15m",
        "command": ["freqtrade", "backtesting"],
        "returncode": 0,
        "metrics": metrics
        or {
            "profit_total_pct": 0.12,
            "max_drawdown": 0.08,
            "sharpe": 1.2,
            "win_rate": 0.57,
            "total_trades": 42,
            "profit_factor": 1.35,
        },
        "raw_result_path": "results/demo.json",
        "error": None,
    }
    payload.update(extra)
    return payload


class TestSanitizeAndParamBuilding(unittest.TestCase):
    def test_sanitize_mapping_filters_sensitive_fields_recursively(self) -> None:
        data = {
            "bb_window": 400,
            "api_secret": "abc",
            "nested": {
                "token": "123",
                "pairs": ("BTC/USDT", "ETH/USDT"),
            },
        }

        sanitized = sanitize_mapping(data)

        self.assertEqual(sanitized["bb_window"], 400)
        self.assertNotIn("api_secret", sanitized)
        self.assertNotIn("token", sanitized["nested"])
        self.assertEqual(sanitized["nested"]["pairs"], ["BTC/USDT", "ETH/USDT"])

    def test_build_backtest_params_whitelists_runner_fields_only(self) -> None:
        candidate = {
            "pairs": ["BTC/USDT", "ETH/USDT"],
            "stake_amount": "100",
            "max_open_trades": "3",
            "bb_window": 400,
            "api_secret": "hidden",
        }

        params = build_backtest_params(candidate)

        self.assertEqual(params["pairs"], ["BTC/USDT", "ETH/USDT"])
        self.assertEqual(params["stake_amount"], 100.0)
        self.assertEqual(params["max_open_trades"], 3)
        self.assertNotIn("bb_window", params)
        self.assertNotIn("api_secret", params)


class TestMetricNormalization(unittest.TestCase):
    def test_normalize_backtest_metrics_supports_aliases(self) -> None:
        raw = {
            "profit_total_pct": 0.125,
            "max_drawdown": 0.08,
            "win_rate": 0.55,
            "total_trades": 25,
            "profit_factor": 1.4,
        }

        metrics = normalize_backtest_metrics(raw)

        self.assertEqual(metrics["total_profit_pct"], 12.5)
        self.assertEqual(metrics["max_drawdown_pct"], 8.0)
        self.assertEqual(metrics["winrate"], 55.0)
        self.assertEqual(metrics["trade_count"], 25.0)
        self.assertEqual(metrics["profit_factor"], 1.4)

    def test_normalize_backtest_metrics_handles_non_numeric_values(self) -> None:
        raw = {
            "total_profit_pct": "12.5",
            "max_drawdown": "nan",
            "sharpe": "inf",
            "win_rate": None,
            "total_trades": {},
        }

        metrics = normalize_backtest_metrics(raw)

        self.assertEqual(metrics["total_profit_pct"], 12.5)
        self.assertEqual(metrics["max_drawdown_pct"], 0.0)
        self.assertEqual(metrics["sharpe"], 0.0)
        self.assertEqual(metrics["winrate"], 0.0)
        self.assertEqual(metrics["trade_count"], 0.0)


class TestFitnessScore(unittest.TestCase):
    def test_compute_fitness_score_prefers_better_metrics(self) -> None:
        config = _fitness_config()
        better = {
            "total_profit_pct": 25.0,
            "max_drawdown_pct": 5.0,
            "sharpe": 1.5,
            "winrate": 60.0,
            "trade_count": 30.0,
        }
        worse = {
            "total_profit_pct": 10.0,
            "max_drawdown_pct": 15.0,
            "sharpe": 0.5,
            "winrate": 40.0,
            "trade_count": 30.0,
        }

        self.assertGreater(compute_fitness_score(better, config), compute_fitness_score(worse, config))

    def test_compute_fitness_score_penalizes_low_trades(self) -> None:
        config = _fitness_config(min_trades=10)
        metrics = {
            "total_profit_pct": 20.0,
            "max_drawdown_pct": 5.0,
            "sharpe": 1.0,
            "winrate": 55.0,
            "trade_count": 3.0,
        }

        self.assertEqual(compute_fitness_score(metrics, config), config.failed_score / 2.0)

    def test_compute_fitness_score_penalizes_drawdown_limit(self) -> None:
        config = _fitness_config(max_drawdown_pct=10.0)
        metrics = {
            "total_profit_pct": 20.0,
            "max_drawdown_pct": 15.0,
            "sharpe": 1.0,
            "winrate": 55.0,
            "trade_count": 30.0,
        }

        self.assertEqual(compute_fitness_score(metrics, config), config.failed_score / 4.0)

    def test_compute_fitness_score_never_returns_nan(self) -> None:
        config = _fitness_config()
        score = compute_fitness_score({"sharpe": "nan", "trade_count": 10}, config)
        self.assertTrue(math.isfinite(score))


class TestEvaluateCandidate(unittest.TestCase):
    def test_evaluate_candidate_success_path_returns_score_and_metrics(self) -> None:
        seen: dict[str, object] = {}

        def runner(**kwargs: object) -> dict:
            seen.update(kwargs)
            return _success_runner()

        result = evaluate_candidate(
            {"bb_window": 400, "stake_amount": 100.0},
            _fitness_config(),
            runner=runner,
        )

        self.assertTrue(result.success)
        self.assertIsInstance(result.fitness_score, float)
        self.assertEqual(result.metrics["trade_count"], 42.0)
        self.assertEqual(result.params["bb_window"], 400)
        self.assertEqual(seen["timeframe"], "15m")
        self.assertEqual(seen["extra_args"]["stake_amount"], 100.0)
        self.assertEqual(seen["extra_args"]["pairs"], ["BTC/USDT"])

    def test_evaluate_candidate_runner_failure_returns_failed_score(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(),
            runner=lambda **_: {"success": False, "error": "invalid json"},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.fitness_score, _fitness_config().failed_score)
        self.assertIn("invalid json", result.reason or "")

    def test_evaluate_candidate_handles_missing_metrics_without_crashing(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(min_trades=0),
            runner=lambda **_: _success_runner(metrics={"profit_total_pct": 0.05}),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.metrics["sharpe"], 0.0)
        self.assertEqual(result.metrics["trade_count"], 0.0)

    def test_evaluate_candidate_marks_trade_count_constraint_in_reason(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(min_trades=50),
            runner=lambda **_: _success_runner(metrics={"total_profit_pct": 20.0, "trade_count": 4}),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.fitness_score, _fitness_config(min_trades=50).failed_score / 2.0)
        self.assertIn("trade_count_below_minimum", result.reason or "")

    def test_evaluate_candidate_marks_drawdown_constraint_in_reason(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(max_drawdown_pct=5.0),
            runner=lambda **_: _success_runner(metrics={"total_profit_pct": 20.0, "trade_count": 30, "max_drawdown": 0.10}),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.fitness_score, _fitness_config(max_drawdown_pct=5.0).failed_score / 4.0)
        self.assertIn("max_drawdown_above_limit", result.reason or "")

    def test_evaluate_candidate_filters_sensitive_candidate_fields_everywhere(self) -> None:
        seen: dict[str, object] = {}

        def runner(**kwargs: object) -> dict:
            seen.update(kwargs)
            return _success_runner()

        candidate = {
            "bb_window": 400,
            "api_secret": "abc",
            "private_key": "xyz",
            "token": "123",
            "stake_amount": 100,
        }
        result = evaluate_candidate(candidate, _fitness_config(), runner=runner)

        self.assertNotIn("api_secret", result.params)
        self.assertNotIn("private_key", result.params)
        self.assertNotIn("token", result.params)
        self.assertNotIn("api_secret", seen["extra_args"])

    def test_unknown_fields_stay_out_of_runner_args(self) -> None:
        seen: dict[str, object] = {}

        def runner(**kwargs: object) -> dict:
            seen.update(kwargs)
            return _success_runner()

        result = evaluate_candidate(
            {"custom_note": "keep", "bb_window": 400},
            _fitness_config(),
            runner=runner,
        )

        self.assertEqual(result.params["custom_note"], "keep")
        self.assertNotIn("custom_note", seen["extra_args"])

    def test_timeout_reason_is_preserved(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(),
            runner=lambda **_: {"success": False, "error": "backtest timed out after 10 seconds"},
        )
        self.assertIn("timed out", result.reason or "")

    def test_missing_result_file_reason_is_preserved(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(),
            runner=lambda **_: {"success": False, "error": "backtest completed but result file was not found"},
        )
        self.assertIn("result file was not found", result.reason or "")

    def test_invalid_json_reason_is_preserved(self) -> None:
        result = evaluate_candidate(
            {"bb_window": 400},
            _fitness_config(),
            runner=lambda **_: {"success": False, "error": "invalid json"},
        )
        self.assertIn("invalid json", result.reason or "")

    def test_candidate_timeframe_overrides_config_timeframe(self) -> None:
        seen: dict[str, object] = {}

        def runner(**kwargs: object) -> dict:
            seen.update(kwargs)
            return _success_runner()

        evaluate_candidate(
            {"timeframe": "1h"},
            _fitness_config(timeframe="15m"),
            runner=runner,
        )

        self.assertEqual(seen["timeframe"], "1h")

    def test_same_candidate_and_metrics_are_deterministic(self) -> None:
        candidate = {"bb_window": 400}
        config = _fitness_config()
        runner = lambda **_: _success_runner()

        first = evaluate_candidate(candidate, config, runner=runner)
        second = evaluate_candidate(candidate, config, runner=runner)

        self.assertEqual(first.fitness_score, second.fitness_score)
        self.assertEqual(first.metrics, second.metrics)

    def test_invalid_candidate_type_returns_failed_result(self) -> None:
        result = evaluate_candidate(["not", "a", "mapping"], _fitness_config())
        self.assertFalse(result.success)
        self.assertEqual(result.fitness_score, _fitness_config().failed_score)


class TestEvaluationArtifacts(unittest.TestCase):
    def test_write_evaluation_artifact_outputs_json_without_secrets(self) -> None:
        result = FitnessResult(
            success=True,
            fitness_score=12.5,
            metrics={"total_profit_pct": 12.5},
            params={"bb_window": 400, "api_secret": "hidden"},
            reason=None,
            backtest_result={"raw_result_path": "results/demo.json", "stdout": "secret=oops"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = write_evaluation_artifact(result, temp_dir, run_id="run-1")
            payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))

        self.assertTrue(Path(artifact_path).name.startswith("evaluation-"))
        self.assertEqual(payload["fitness_score"], 12.5)
        self.assertEqual(payload["params"]["bb_window"], 400)
        self.assertNotIn("api_secret", payload["params"])
        self.assertEqual(payload["run_id"], "run-1")
        self.assertIn("created_at", payload)

    def test_failed_result_artifact_also_writes_reason(self) -> None:
        result = FitnessResult(
            success=False,
            fitness_score=-1_000_000.0,
            metrics={},
            params={"bb_window": 400},
            reason="backtest_runner_failed: invalid json",
            backtest_result={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = write_evaluation_artifact(result, temp_dir)
            payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))

        self.assertFalse(payload["success"])
        self.assertIn("invalid json", payload["reason"])

    def test_evaluate_candidate_can_write_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = evaluate_candidate(
                {"bb_window": 400, "token": "hidden"},
                _fitness_config(),
                runner=lambda **_: _success_runner(),
                artifact_dir=temp_dir,
            )
            artifact_path = Path(result.artifact_path)
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertIsNotNone(result.artifact_path)
            self.assertTrue(artifact_path.exists())
            self.assertNotIn("token", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()

"""Real backtest evaluation adapter with safe default-disabled execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import FitnessConfig, sanitize_mapping
from bollinger_evolver.ga.generation_runner import GenerationConfig, candidate_id
from bollinger_evolver.ga.population_ops import extract_gene_snapshot
from bollinger_evolver.runners.backtest_runner import run_backtest
from bollinger_evolver.scoring.fitness import calculate_fitness
from bollinger_evolver.strategy_factory import GENERATED_ROOT, generate_strategy_from_genes


FAILED_SCORE = -1_000_000.0
SENSITIVE_KEYS = (
    "api_key",
    "secret",
    "private_key",
    "password",
    "token",
    "webhook",
    "mnemonic",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower()
    return any(marker in normalized for marker in SENSITIVE_KEYS)


def _filter_sensitive(data: Any) -> Any:
    if isinstance(data, Mapping):
        return {
            key: _filter_sensitive(value)
            for key, value in data.items()
            if not _is_sensitive_key(str(key))
        }
    if isinstance(data, list):
        return [_filter_sensitive(item) for item in data]
    if isinstance(data, tuple):
        return tuple(_filter_sensitive(item) for item in data)
    return data


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_numeric(metrics: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _to_float(metrics.get(key))
        if value is not None:
            return value
    return None


def _first_int(metrics: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = _to_int(metrics.get(key))
        if value is not None:
            return value
    return None


def calculate_basic_backtest_fitness(metrics: Mapping[str, Any]) -> tuple[float | None, dict[str, Any]]:
    """Temporary conservative fitness from parsed Freqtrade backtest metrics."""

    safe_metrics = sanitize_mapping(_filter_sensitive(metrics))
    total_profit = _first_numeric(
        safe_metrics,
        ("profit_total_pct", "total_profit_pct", "total_profit", "profit_total"),
    )
    max_drawdown = _first_numeric(
        safe_metrics,
        ("max_drawdown_pct", "max_drawdown", "drawdown_max"),
    )
    profit_factor = _first_numeric(safe_metrics, ("profit_factor",))
    trade_count = _first_int(safe_metrics, ("trade_count", "total_trades", "trades"))

    breakdown = {
        "accepted": False,
        "reason": None,
        "total_profit": total_profit,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "trade_count": trade_count,
        "fitness": None,
    }

    if total_profit is None:
        breakdown["reason"] = "missing_total_profit"
        return None, breakdown
    if total_profit <= 0:
        breakdown["reason"] = "nonpositive_total_profit"
        return None, breakdown
    if trade_count is None:
        breakdown["reason"] = "missing_trade_count"
        return None, breakdown
    if trade_count < 1:
        breakdown["reason"] = "low_trade_count"
        return None, breakdown
    if profit_factor is None:
        breakdown["reason"] = "missing_profit_factor"
        return None, breakdown
    if profit_factor < 1.0:
        breakdown["reason"] = "low_profit_factor"
        return None, breakdown
    if max_drawdown is None:
        breakdown["reason"] = "missing_max_drawdown"
        return None, breakdown
    if max_drawdown > 50.0:
        breakdown["reason"] = "max_drawdown_too_high"
        return None, breakdown

    fitness = (
        float(total_profit)
        + (float(profit_factor) * 5.0)
        + (min(float(trade_count), 200.0) * 0.02)
        - (float(max_drawdown) * 1.5)
    )
    breakdown.update(
        {
            "accepted": True,
            "reason": "accepted",
            "fitness": fitness,
        }
    )
    return fitness, breakdown


class BacktestEvaluationAdapter:
    """Generate a strategy, then optionally run a real Freqtrade backtest."""

    def __init__(
        self,
        *,
        config_path: str,
        timerange: str,
        timeframe: str = "15m",
        strategy_output_dir: str | Path | None = None,
        export_dir: str | Path = "results/bollinger_evolver/backtests",
        allow_real_backtest: bool = False,
        runner: Callable[..., Mapping[str, Any]] | None = None,
        timeout_seconds: int = 3600,
        overwrite: bool = False,
        extra_args: Mapping[str, Any] | None = None,
        data_coverage_manifest: Mapping[str, Any] | None = None,
        data_quality_gate_enabled: bool = True,
        required_pairs: list[str] | None = None,
        required_timeframes: list[str] | None = None,
        min_candles_per_pair_timeframe: int = 100,
        max_gap_ratio: float = 0.02,
        allow_invalid_ohlc: bool = False,
    ) -> None:
        self.config_path = config_path
        self.timerange = timerange
        self.timeframe = timeframe
        self.strategy_output_dir = Path(strategy_output_dir) if strategy_output_dir else GENERATED_ROOT / "backtest_adapter"
        self.export_dir = str(export_dir)
        self.allow_real_backtest = allow_real_backtest
        self.runner = runner or run_backtest
        self.timeout_seconds = timeout_seconds
        self.overwrite = overwrite
        self.extra_args = dict(_filter_sensitive(extra_args or {}))
        self.data_coverage_manifest = sanitize_mapping(_filter_sensitive(data_coverage_manifest)) if data_coverage_manifest is not None else None
        self.data_quality_gate_enabled = data_quality_gate_enabled
        self.required_pairs = list(required_pairs) if required_pairs is not None else None
        self.required_timeframes = list(required_timeframes) if required_timeframes is not None else None
        self.min_candles_per_pair_timeframe = min_candles_per_pair_timeframe
        self.max_gap_ratio = max_gap_ratio
        self.allow_invalid_ohlc = allow_invalid_ohlc

    def __call__(
        self,
        individual: Mapping[str, Any],
        fitness_config: FitnessConfig,
        *,
        generation_config: GenerationConfig | None = None,
        individual_index: int = 0,
    ) -> dict[str, Any]:
        generation = generation_config.generation_index if generation_config else 0
        output_root = generation_config.output_dir if generation_config else self.export_dir
        return self.evaluate(
            individual,
            generation=generation,
            output_root=str(output_root),
            individual_index=individual_index,
            failed_score=getattr(fitness_config, "failed_score", FAILED_SCORE),
        )

    def evaluate(
        self,
        individual: Mapping[str, Any],
        *,
        generation: int,
        output_root: str | None = None,
        individual_index: int = 0,
        failed_score: float = FAILED_SCORE,
    ) -> dict[str, Any]:
        safe_individual = sanitize_mapping(_filter_sensitive(individual))
        genes = extract_gene_snapshot(safe_individual)
        individual_id = candidate_id(genes or safe_individual)
        data_quality_gate = self._data_quality_gate()

        if data_quality_gate is not None and not data_quality_gate.get("allowed_for_evaluation"):
            error = (
                "data_quality_manifest_missing"
                if data_quality_gate.get("status") == "MISSING"
                else "data_quality_gate_failed"
            )
            return self._failure_result(
                individual_id=individual_id,
                generation=generation,
                genes=genes,
                strategy_info=None,
                error=error,
                real_backtest=False,
                failed_score=failed_score,
                metrics={"dataQualityGate": data_quality_gate},
            )

        try:
            strategy_info = generate_strategy_from_genes(
                dict(genes),
                generation=generation,
                individual_index=individual_index,
                output_dir=str(self.strategy_output_dir),
                overwrite=self.overwrite,
            )
        except Exception as exc:
            return self._failure_result(
                individual_id=individual_id,
                generation=generation,
                genes=genes,
                strategy_info=None,
                error=str(exc),
                real_backtest=False,
                failed_score=failed_score,
                metrics={"dataQualityGate": data_quality_gate} if data_quality_gate else None,
            )

        if not self.allow_real_backtest:
            return self._failure_result(
                individual_id=individual_id,
                generation=generation,
                genes=genes,
                strategy_info=strategy_info,
                error="real_backtest_disabled",
                real_backtest=False,
                failed_score=failed_score,
                metrics={"dataQualityGate": data_quality_gate} if data_quality_gate else None,
            )

        runner_result = self.runner(
            strategy_name=strategy_info["strategy_name"],
            config_path=self.config_path,
            timerange=self.timerange,
            timeframe=self.timeframe,
            strategy_path=strategy_info["output_path"],
            export_dir=self.export_dir,
            extra_args=self.extra_args,
            timeout_seconds=self.timeout_seconds,
        )
        safe_runner_result = sanitize_mapping(_filter_sensitive(runner_result))
        metrics = sanitize_mapping(_filter_sensitive(safe_runner_result.get("metrics", {})))
        metrics["mock"] = False
        metrics["real_backtest"] = True
        if data_quality_gate is not None:
            metrics["dataQualityGate"] = data_quality_gate

        if not safe_runner_result.get("success"):
            return self._failure_result(
                individual_id=individual_id,
                generation=generation,
                genes=genes,
                strategy_info=strategy_info,
                error=str(safe_runner_result.get("error") or "backtest_failed"),
                real_backtest=True,
                failed_score=failed_score,
                metrics=metrics,
            )

        fitness, breakdown = calculate_fitness(metrics, genes=genes)
        metrics["fitness_breakdown"] = breakdown
        if not breakdown.get("accepted"):
            return self._failure_result(
                individual_id=individual_id,
                generation=generation,
                genes=genes,
                strategy_info=strategy_info,
                error=str(breakdown.get("reject_reason") or "insufficient_backtest_metrics"),
                real_backtest=True,
                failed_score=failed_score,
                metrics=metrics,
            )

        params = self._params(
            individual_id=individual_id,
            strategy_info=strategy_info,
            real_backtest=True,
        )
        return {
            "success": True,
            "individual_id": individual_id,
            "generation": generation,
            "strategy_name": strategy_info["strategy_name"],
            "strategy_path": strategy_info["output_path"],
            "genes_hash": strategy_info["genes_hash"],
            "fitness": fitness,
            "fitness_score": fitness,
            "metrics": metrics,
            "genes": genes,
            "params": params,
            "error": None,
            "reason": None,
            "mock_evaluation": False,
            "real_backtest": True,
        }

    def _params(
        self,
        *,
        individual_id: str,
        strategy_info: Mapping[str, Any] | None,
        real_backtest: bool,
    ) -> dict[str, Any]:
        params = {
            "individual_id": individual_id,
            "mock_evaluation": False,
            "real_backtest": real_backtest,
        }
        if strategy_info:
            params.update(
                {
                    "strategy_name": strategy_info["strategy_name"],
                    "strategy_path": strategy_info["output_path"],
                    "genes_hash": strategy_info["genes_hash"],
                    "gene_id": strategy_info["gene_id"],
                }
            )
        return sanitize_mapping(_filter_sensitive(params))

    def _data_quality_gate(self) -> dict[str, Any] | None:
        if not self.data_quality_gate_enabled:
            return None
        gate = evaluate_data_coverage_gate(
            dict(self.data_coverage_manifest) if self.data_coverage_manifest is not None else None,
            required_pairs=self.required_pairs,
            required_timeframes=self.required_timeframes or ([self.timeframe] if self.timeframe else None),
            min_candles_per_pair_timeframe=self.min_candles_per_pair_timeframe,
            max_gap_ratio=self.max_gap_ratio,
            allow_invalid_ohlc=self.allow_invalid_ohlc,
        )
        return sanitize_mapping(_filter_sensitive(gate))

    def _failure_result(
        self,
        *,
        individual_id: str,
        generation: int,
        genes: Mapping[str, Any],
        strategy_info: Mapping[str, Any] | None,
        error: str,
        real_backtest: bool,
        failed_score: float,
        metrics: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_metrics = sanitize_mapping(_filter_sensitive(metrics or {}))
        safe_metrics.setdefault("mock", False)
        safe_metrics.setdefault("real_backtest", real_backtest)
        return {
            "success": False,
            "individual_id": individual_id,
            "generation": generation,
            "strategy_name": strategy_info["strategy_name"] if strategy_info else None,
            "strategy_path": strategy_info["output_path"] if strategy_info else None,
            "genes_hash": strategy_info["genes_hash"] if strategy_info else None,
            "fitness": None,
            "fitness_score": float(failed_score),
            "metrics": safe_metrics,
            "genes": sanitize_mapping(_filter_sensitive(genes)),
            "params": self._params(
                individual_id=individual_id,
                strategy_info=strategy_info,
                real_backtest=real_backtest,
            ),
            "error": error,
            "reason": error,
            "mock_evaluation": False,
            "real_backtest": real_backtest,
        }

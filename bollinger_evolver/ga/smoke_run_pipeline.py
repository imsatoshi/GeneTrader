"""End-to-end GA smoke run pipeline for Bollinger Evolver."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.evaluators import FitnessConfig, sanitize_mapping
from bollinger_evolver.ga.backtest_evaluation_adapter import BacktestEvaluationAdapter
from bollinger_evolver.ga.evaluation_pipeline import MockStrategyEvaluator
from bollinger_evolver.ga.generation_runner import GenerationConfig, candidate_id
from bollinger_evolver.ga.orchestrator import GAOrchestratorConfig, GAOrchestratorResult, run_ga
from bollinger_evolver.ga.population_ops import normalize_candidate_genes
from bollinger_evolver.gene_space import load_gene_space, sample_genes
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES
from bollinger_evolver.strategies.position_sizing import (
    calculate_dca_stake,
    calculate_leverage,
    calculate_stake_amount,
    calculate_stoploss_from_atr,
    should_reduce_position,
)
from bollinger_evolver.strategy_factory import GENERATED_ROOT


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SmokeRunConfig:
    generations: int = 2
    population_size: int = 4
    seed: int = 123
    run_id: str = "smoke-run"
    output_root: Path | str = "results/bollinger_evolver/smoke_runs"
    strategy_output_dir: Path | str | None = None
    evaluation_mode: str = "mock"
    allow_real_backtest: bool = False
    elite_count: int = 1
    mutation_rate: float = 0.2
    crossover_rate: float = 0.8
    fail_individual_indexes: tuple[int, ...] = ()
    data_coverage_manifest: Mapping[str, Any] | None = None
    data_quality_gate_enabled: bool = True
    required_pairs: tuple[str, ...] = ("BTC/USDT",)
    required_timeframes: tuple[str, ...] = ("15m",)
    min_candles_per_pair_timeframe: int = 100
    max_gap_ratio: float = 0.02
    allow_invalid_ohlc: bool = False


def _resolve_path(path_value: Path | str) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _default_strategy_output_dir(config: SmokeRunConfig) -> Path:
    return GENERATED_ROOT / "smoke_runs" / config.run_id


def _default_smoke_manifest(config: SmokeRunConfig) -> dict[str, Any]:
    entries = []
    for pair in config.required_pairs:
        for timeframe in config.required_timeframes:
            entries.append(
                {
                    "pair": pair,
                    "timeframe": timeframe,
                    "status": "ready",
                    "row_count": 500,
                    "gap_count": 0,
                    "invalid_ohlc_count": 0,
                    "covers_start_date": True,
                }
            )
    return {
        "status": "ready",
        "pairs": list(config.required_pairs),
        "timeframes": list(config.required_timeframes),
        "expected_file_count": len(entries),
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": 0,
        "gap_count": 0,
        "entries": entries,
    }


def build_smoke_initial_population(
    *,
    population_size: int,
    seed: int,
    initial_population: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build a deterministic, complete gene population from DEFAULT_GENES."""

    if population_size <= 0:
        return []

    rng = random.Random(seed)
    gene_space = load_gene_space()
    provided = list(initial_population or [])
    population: list[dict[str, Any]] = []

    for candidate in provided[:population_size]:
        if isinstance(candidate, Mapping):
            population.append(normalize_candidate_genes(candidate, gene_space, rng=rng))

    if not population:
        population.append(normalize_candidate_genes(dict(DEFAULT_GENES), gene_space, rng=rng))

    while len(population) < population_size:
        sampled = dict(DEFAULT_GENES)
        sampled.update(sample_genes(gene_space, rng=rng))
        population.append(normalize_candidate_genes(sampled, gene_space, rng=rng))

    return population[:population_size]


def build_position_sizing_snapshot(
    genes: Mapping[str, Any],
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute deterministic position sizing smoke values from genes and metrics."""

    safe_genes = sanitize_mapping(genes)
    safe_metrics = sanitize_mapping(metrics or {})
    score = float(safe_metrics.get("win_rate", safe_genes.get("min_long_score", 75.0)) or 75.0)
    stoploss = calculate_stoploss_from_atr(
        atr=2.0,
        current_rate=100.0,
        atr_stop_mult=float(safe_genes.get("atr_stop_mult", DEFAULT_GENES["atr_stop_mult"])),
        max_position_risk=float(
            safe_genes.get("max_position_risk", DEFAULT_GENES["max_position_risk"])
        ),
    )
    stop_distance_ratio = abs(stoploss)
    stake_amount = calculate_stake_amount(
        available_stake=1000.0,
        score=score,
        stop_distance_ratio=stop_distance_ratio,
        genes=safe_genes,
        min_stake=5.0,
        max_stake=500.0,
    )
    dca_stake = calculate_dca_stake(
        current_stake=max(stake_amount, 100.0),
        score=score,
        current_profit=-0.04,
        successful_entries=1,
        has_open_orders=False,
        four_hour_regime_ok=score >= 60.0,
        genes=safe_genes,
    )
    leverage = calculate_leverage(
        score=score,
        max_leverage=10.0,
        trading_mode="futures",
        genes=safe_genes,
    )
    return {
        "score": score,
        "custom_stake_amount": stake_amount,
        "adjust_trade_position": dca_stake,
        "leverage": leverage,
        "stoploss": stoploss,
        "reduce_position_action": should_reduce_position(score),
    }


class PositionSizingSmokeEvaluator:
    """Wrap a GA evaluator and attach position sizing metadata to each result."""

    def __init__(
        self,
        base_evaluator: Any,
        *,
        fail_individual_indexes: tuple[int, ...] = (),
    ) -> None:
        self.base_evaluator = base_evaluator
        self.fail_individual_indexes = set(fail_individual_indexes)

    def __call__(
        self,
        individual: Mapping[str, Any],
        fitness_config: FitnessConfig,
        *,
        generation_config: GenerationConfig | None = None,
        individual_index: int = 0,
    ) -> dict[str, Any]:
        safe_individual = sanitize_mapping(individual)
        if individual_index in self.fail_individual_indexes:
            return {
                "success": False,
                "individual_id": candidate_id(safe_individual),
                "generation": generation_config.generation_index if generation_config else 0,
                "fitness": None,
                "fitness_score": fitness_config.failed_score,
                "metrics": {"mock": True, "forced_failure": True},
                "genes": safe_individual,
                "params": {"mock_evaluation": True, "forced_failure": True},
                "error": "forced_smoke_failure",
                "reason": "forced_smoke_failure",
            }

        result = self.base_evaluator(
            individual,
            fitness_config,
            generation_config=generation_config,
            individual_index=individual_index,
        )
        if not isinstance(result, Mapping):
            return result

        enriched = dict(result)
        metrics = sanitize_mapping(enriched.get("metrics", {}))
        genes = sanitize_mapping(enriched.get("genes", safe_individual))
        position_sizing = build_position_sizing_snapshot(genes, metrics)
        params = sanitize_mapping(enriched.get("params", {}))

        metrics["position_sizing"] = position_sizing
        params["position_sizing"] = position_sizing
        enriched["metrics"] = metrics
        enriched["params"] = params
        enriched["genes"] = genes
        return enriched


def _build_fitness_config(config: SmokeRunConfig, output_root: Path) -> FitnessConfig:
    return FitnessConfig(
        strategy="BollingerResonanceSmoke",
        config_path=output_root / "config.json",
        timerange="20240101-20240201",
        timeframe="15m",
        pairs=("BTC/USDT",),
        result_dir=output_root / "backtests",
        timeout_seconds=120,
        failed_score=-1_000_000.0,
    )


def _build_base_evaluator(
    config: SmokeRunConfig,
    output_root: Path,
    strategy_output_dir: Path,
) -> Any:
    if config.evaluation_mode == "mock":
        return MockStrategyEvaluator(
            seed=config.seed,
            output_root=output_root,
            strategy_output_dir=strategy_output_dir,
            overwrite=True,
            data_coverage_manifest=config.data_coverage_manifest or _default_smoke_manifest(config),
            data_quality_gate_enabled=config.data_quality_gate_enabled,
            required_pairs=list(config.required_pairs),
            required_timeframes=list(config.required_timeframes),
            min_candles_per_pair_timeframe=config.min_candles_per_pair_timeframe,
            max_gap_ratio=config.max_gap_ratio,
            allow_invalid_ohlc=config.allow_invalid_ohlc,
        )
    if config.evaluation_mode == "backtest_disabled":
        if config.allow_real_backtest:
            raise ValueError(
                "backtest_disabled mode cannot enable real backtesting. "
                "Use a dedicated real-backtest integration path instead."
            )
        return BacktestEvaluationAdapter(
            config_path=str(output_root / "config.json"),
            timerange="20240101-20240201",
            strategy_output_dir=strategy_output_dir,
            export_dir=output_root / "backtests",
            allow_real_backtest=False,
            overwrite=True,
            data_coverage_manifest=config.data_coverage_manifest,
            data_quality_gate_enabled=config.data_quality_gate_enabled,
            required_pairs=list(config.required_pairs),
            required_timeframes=list(config.required_timeframes),
            min_candles_per_pair_timeframe=config.min_candles_per_pair_timeframe,
            max_gap_ratio=config.max_gap_ratio,
            allow_invalid_ohlc=config.allow_invalid_ohlc,
        )
    raise ValueError("evaluation_mode must be 'mock' or 'backtest_disabled'.")


def run_smoke_ga_pipeline(
    config: SmokeRunConfig | None = None,
    *,
    initial_population: list[dict[str, Any]] | None = None,
) -> GAOrchestratorResult:
    """Run a deterministic multi-generation GA smoke pipeline without Freqtrade."""

    resolved_config = config or SmokeRunConfig()
    output_root = _resolve_path(resolved_config.output_root)
    strategy_output_dir = (
        _resolve_path(resolved_config.strategy_output_dir)
        if resolved_config.strategy_output_dir is not None
        else _default_strategy_output_dir(resolved_config)
    )
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "config.json").write_text("{}", encoding="utf-8")

    population = build_smoke_initial_population(
        population_size=resolved_config.population_size,
        seed=resolved_config.seed,
        initial_population=initial_population,
    )
    fitness_config = _build_fitness_config(resolved_config, output_root)
    base_evaluator = _build_base_evaluator(
        resolved_config,
        output_root,
        strategy_output_dir,
    )
    evaluator = PositionSizingSmokeEvaluator(
        base_evaluator,
        fail_individual_indexes=resolved_config.fail_individual_indexes,
    )
    orchestrator_config = GAOrchestratorConfig(
        generations=resolved_config.generations,
        population_size=resolved_config.population_size,
        run_id=resolved_config.run_id,
        seed=resolved_config.seed,
        run_output_dir=output_root / "runs",
        generation_output_dir=output_root / "generations",
        best_output_dir=output_root / "best",
        elite_count=resolved_config.elite_count,
        mutation_rate=resolved_config.mutation_rate,
        crossover_rate=resolved_config.crossover_rate,
        mode=resolved_config.evaluation_mode,
    )
    return run_ga(
        population,
        fitness_config,
        orchestrator_config,
        evaluator=evaluator,
    )

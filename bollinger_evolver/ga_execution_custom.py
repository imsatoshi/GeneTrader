"""Custom strategy GA execution scaffold for mock-first evaluation."""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from bollinger_evolver.backtest_adapter import run_mock_backtest
from bollinger_evolver.custom_strategy_schema import (
    CUSTOM_STRATEGY_PARAMETER_NAMES,
    CustomStrategyBounds,
    CustomStrategyGenome,
    ParameterBound,
    custom_strategy_config_from_genome,
    validate_custom_strategy_genome,
)
from bollinger_evolver.fitness import calculate_risk_aware_fitness_breakdown
from bollinger_evolver.risk_governor import RiskGovernorConfig, apply_risk_governor


@dataclass(frozen=True)
class CustomGAExecutionConfig:
    population_size: int = 12
    generations: int = 3
    seed: int = 0
    elite_count: int = 2
    mutation_rate: float = 0.18
    crossover_rate: float = 0.75
    top_n: int = 5
    pair: str = "BTC/USDT"
    timeframe: str = "1h"
    trade_count: int = 100


@dataclass(frozen=True)
class CustomFitnessEvaluation:
    genome: CustomStrategyGenome
    strategy_config: Mapping[str, Any]
    adjusted_strategy_config: Mapping[str, Any]
    mock_backtest: Mapping[str, Any]
    risk_governor: Mapping[str, Any]
    fitness: float
    fitness_components: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        json.dumps(data, sort_keys=True)
        return data


@dataclass(frozen=True)
class CustomGenerationResult:
    generation: int
    population: list[CustomStrategyGenome]
    evaluations: list[CustomFitnessEvaluation]
    best: CustomFitnessEvaluation
    average_fitness: float
    diversity: float


@dataclass(frozen=True)
class CustomGAExecutionResult:
    config: CustomGAExecutionConfig
    generations: list[CustomGenerationResult] = field(default_factory=list)
    run_id: str = ""

    @property
    def final_best(self) -> CustomFitnessEvaluation | None:
        if not self.generations:
            return None
        return max((item.best for item in self.generations), key=lambda item: item.fitness)


def _sample_value(bound: ParameterBound, rng: random.Random) -> int | float:
    if bound.kind == "int":
        return rng.randint(int(bound.minimum), int(bound.maximum))
    return round(rng.uniform(bound.minimum, bound.maximum), 6)


def _coerce_value(value: int | float, bound: ParameterBound) -> int | float:
    clipped = max(bound.minimum, min(bound.maximum, float(value)))
    if bound.kind == "int":
        return int(round(clipped))
    return round(clipped, 6)


def create_custom_random_genome(
    rng: random.Random,
    genome_id: str,
    *,
    bounds: CustomStrategyBounds | None = None,
) -> CustomStrategyGenome:
    active_bounds = bounds or CustomStrategyBounds()
    payload = {
        name: _sample_value(getattr(active_bounds, name), rng)
        for name in CUSTOM_STRATEGY_PARAMETER_NAMES
    }
    genome = CustomStrategyGenome(genome_id=genome_id, **payload)
    validate_custom_strategy_genome(genome, bounds=active_bounds)
    return genome


def create_custom_population(
    population_size: int,
    rng: random.Random,
    *,
    prefix: str = "custom",
    bounds: CustomStrategyBounds | None = None,
) -> list[CustomStrategyGenome]:
    if population_size <= 0:
        return []
    return [
        create_custom_random_genome(rng, f"{prefix}-{index:03d}", bounds=bounds)
        for index in range(population_size)
    ]


def _custom_parameters(genome: CustomStrategyGenome) -> dict[str, int | float]:
    return {name: getattr(genome, name) for name in CUSTOM_STRATEGY_PARAMETER_NAMES}


def crossover_custom_genomes(
    parent_a: CustomStrategyGenome,
    parent_b: CustomStrategyGenome,
    rng: random.Random,
    child_id: str,
) -> CustomStrategyGenome:
    validate_custom_strategy_genome(parent_a)
    validate_custom_strategy_genome(parent_b)
    payload = {
        name: getattr(parent_a, name) if rng.random() < 0.5 else getattr(parent_b, name)
        for name in CUSTOM_STRATEGY_PARAMETER_NAMES
    }
    child = CustomStrategyGenome(genome_id=child_id, **payload)
    validate_custom_strategy_genome(child)
    return child


def mutate_custom_genome(
    genome: CustomStrategyGenome,
    rng: random.Random,
    *,
    mutation_rate: float,
    genome_id: str | None = None,
    bounds: CustomStrategyBounds | None = None,
) -> CustomStrategyGenome:
    validate_custom_strategy_genome(genome, bounds=bounds)
    active_bounds = bounds or CustomStrategyBounds()
    payload = _custom_parameters(genome)
    for name in CUSTOM_STRATEGY_PARAMETER_NAMES:
        if rng.random() >= max(0.0, min(1.0, mutation_rate)):
            continue
        bound = getattr(active_bounds, name)
        value = payload[name]
        if bound.kind == "int":
            payload[name] = _coerce_value(int(value) + rng.choice([-2, -1, 1, 2]), bound)
        else:
            span = bound.maximum - bound.minimum
            payload[name] = _coerce_value(float(value) + rng.uniform(-0.10 * span, 0.10 * span), bound)
    mutated = CustomStrategyGenome(genome_id=genome_id or genome.genome_id, **payload)
    validate_custom_strategy_genome(mutated, bounds=active_bounds)
    return mutated


def _apply_risk_adjustments(strategy_config: Mapping[str, Any], advice: Mapping[str, Any]) -> dict[str, Any]:
    adjusted = json.loads(json.dumps(strategy_config, sort_keys=True))
    adjusted["leverage"] = float(advice["adjusted_leverage"])
    adjusted["risk_per_trade"] = float(advice["adjusted_risk_per_trade"])
    adjusted["position_sizing"]["leverage"] = adjusted["leverage"]
    adjusted["position_sizing"]["risk_per_trade"] = adjusted["risk_per_trade"]
    adjusted["risk_governor_applied"] = True
    return adjusted


def evaluate_custom_genome(
    genome: CustomStrategyGenome,
    *,
    seed: int = 0,
    pair: str = "BTC/USDT",
    timeframe: str = "1h",
    trade_count: int = 100,
    risk_config: RiskGovernorConfig | None = None,
) -> CustomFitnessEvaluation:
    """Evaluate one custom genome through mock backtest and advisory risk governor."""

    strategy_config = custom_strategy_config_from_genome(genome)
    preliminary = run_mock_backtest(
        strategy_config,
        pair=pair,
        timeframe=timeframe,
        trade_count=trade_count,
        seed=seed,
    )
    risk_advice = apply_risk_governor(
        strategy_config,
        {
            "drawdown": preliminary.drawdown,
            "max_consecutive_losses": preliminary.max_loss_streak,
        },
        config=risk_config,
    )
    adjusted_config = _apply_risk_adjustments(strategy_config, risk_advice)
    backtest = run_mock_backtest(
        adjusted_config,
        pair=pair,
        timeframe=timeframe,
        trade_count=trade_count,
        seed=seed,
    )
    fitness_components = calculate_risk_aware_fitness_breakdown(
        profit=backtest.profit,
        drawdown=backtest.drawdown,
        sharpe=backtest.sharpe,
        win_rate=backtest.win_rate,
        leverage=backtest.leverage,
        risk_per_trade=backtest.risk_per_trade,
        max_loss_streak=backtest.max_loss_streak,
    )
    return CustomFitnessEvaluation(
        genome=genome,
        strategy_config=strategy_config,
        adjusted_strategy_config=adjusted_config,
        mock_backtest=backtest.to_dict(),
        risk_governor=risk_advice,
        fitness=float(fitness_components["final_fitness"]),
        fitness_components=fitness_components,
    )


def _average_fitness(evaluations: list[CustomFitnessEvaluation]) -> float:
    if not evaluations:
        return 0.0
    return round(sum(item.fitness for item in evaluations) / len(evaluations), 6)


def _diversity(population: list[CustomStrategyGenome]) -> float:
    if not population:
        return 0.0
    unique = {tuple(sorted(_custom_parameters(item).items())) for item in population}
    return round(len(unique) / len(population), 6)


def _select_elites(evaluations: list[CustomFitnessEvaluation], elite_count: int) -> list[CustomStrategyGenome]:
    ranked = sorted(evaluations, key=lambda item: item.fitness, reverse=True)
    return [item.genome for item in ranked[: max(0, elite_count)]]


def _next_population(
    evaluations: list[CustomFitnessEvaluation],
    config: CustomGAExecutionConfig,
    rng: random.Random,
    generation: int,
) -> list[CustomStrategyGenome]:
    elites = _select_elites(evaluations, config.elite_count)
    if not elites:
        return []
    next_population = [
        CustomStrategyGenome(genome_id=f"custom-gen{generation:03d}-elite{index:03d}", **_custom_parameters(genome))
        for index, genome in enumerate(elites)
    ]
    parent_pool = elites if len(elites) > 1 else [elites[0], elites[0]]
    while len(next_population) < config.population_size:
        child_id = f"custom-gen{generation:03d}-ind{len(next_population):03d}"
        parent_a = rng.choice(parent_pool)
        parent_b = rng.choice(parent_pool)
        if rng.random() < config.crossover_rate:
            child = crossover_custom_genomes(parent_a, parent_b, rng, child_id)
        else:
            child = CustomStrategyGenome(genome_id=child_id, **_custom_parameters(parent_a))
        next_population.append(mutate_custom_genome(child, rng, mutation_rate=config.mutation_rate, genome_id=child_id))
    return next_population[: config.population_size]


def run_custom_ga_execution(
    config: CustomGAExecutionConfig,
    *,
    bounds: CustomStrategyBounds | None = None,
    risk_config: RiskGovernorConfig | None = None,
    run_id: str | None = None,
) -> CustomGAExecutionResult:
    """Run deterministic custom-strategy GA over mock backtests only."""

    if config.population_size <= 0:
        raise ValueError("population_size_must_be_positive")
    if config.generations <= 0:
        raise ValueError("generations_must_be_positive")
    rng = random.Random(config.seed)
    population = create_custom_population(config.population_size, rng, prefix="custom-gen000", bounds=bounds)
    generations: list[CustomGenerationResult] = []
    for generation in range(1, config.generations + 1):
        evaluations = sorted(
            (
                evaluate_custom_genome(
                    genome,
                    seed=config.seed + generation,
                    pair=config.pair,
                    timeframe=config.timeframe,
                    trade_count=config.trade_count,
                    risk_config=risk_config,
                )
                for genome in population
            ),
            key=lambda item: item.fitness,
            reverse=True,
        )
        generations.append(
            CustomGenerationResult(
                generation=generation,
                population=population,
                evaluations=evaluations,
                best=evaluations[0],
                average_fitness=_average_fitness(evaluations),
                diversity=_diversity(population),
            )
        )
        if generation < config.generations:
            population = _next_population(evaluations, config, rng, generation)
    result = CustomGAExecutionResult(
        config=config,
        generations=generations,
        run_id=run_id or f"custom-ga-seed-{config.seed}",
    )
    json.dumps(build_custom_ga_session_summary(result), sort_keys=True)
    return result


def build_custom_ga_session_summary(
    execution_result: CustomGAExecutionResult,
    *,
    top_n: int | None = None,
) -> dict[str, Any]:
    """Build JSON-safe frontend/artifact summary for a custom GA execution."""

    generations = execution_result.generations
    top = top_n if top_n is not None else execution_result.config.top_n
    all_evaluations = [evaluation for generation in generations for evaluation in generation.evaluations]
    leaderboard = sorted((item.to_dict() for item in all_evaluations), key=lambda item: item["fitness"], reverse=True)
    limited = [
        {"rank": index, **entry}
        for index, entry in enumerate(leaderboard[: max(0, int(top))], start=1)
    ]
    series = [
        {
            "generation": generation.generation,
            "best_fitness": round(generation.best.fitness, 6),
            "average_fitness": generation.average_fitness,
            "diversity": generation.diversity,
        }
        for generation in generations
    ]
    best = limited[0] if limited else None
    summary = {
        "schema_version": "custom-ga-session-summary/v1",
        "source": "custom-strategy-mock-ga",
        "run_id": execution_result.run_id,
        "status": "completed" if generations else "empty",
        "generation": generations[-1].generation if generations else 0,
        "population_size": execution_result.config.population_size,
        "best_fitness": best["fitness"] if best else None,
        "best_genome": best["genome"] if best else None,
        "fitness_series": series,
        "leaderboard": limited,
    }
    json.dumps(summary, sort_keys=True)
    return summary

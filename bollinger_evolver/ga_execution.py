"""Lightweight GA execution loop for mock-first Bollinger evolution."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from bollinger_evolver.fitness import FitnessEvaluation, MockEvaluator
from bollinger_evolver.genome import Genome, create_population, crossover_genomes, mutate_genome


@dataclass(frozen=True)
class GAExecutionConfig:
    population_size: int = 12
    generations: int = 3
    seed: int = 0
    elite_count: int = 2
    mutation_rate: float = 0.18
    crossover_rate: float = 0.75


@dataclass(frozen=True)
class GenerationResult:
    generation: int
    population: list[Genome]
    evaluations: list[FitnessEvaluation]
    best: FitnessEvaluation
    average_fitness: float
    diversity: float


@dataclass(frozen=True)
class GAExecutionResult:
    config: GAExecutionConfig
    generations: list[GenerationResult] = field(default_factory=list)

    @property
    def final_best(self) -> FitnessEvaluation | None:
        if not self.generations:
            return None
        return max((item.best for item in self.generations), key=lambda item: item.fitness)


def evaluate_population(population: list[Genome], evaluator: MockEvaluator) -> list[FitnessEvaluation]:
    return [evaluator.evaluate(genome) for genome in population]


def _average_fitness(evaluations: list[FitnessEvaluation]) -> float:
    if not evaluations:
        return 0.0
    return round(sum(item.fitness for item in evaluations) / len(evaluations), 6)


def _diversity(population: list[Genome]) -> float:
    if not population:
        return 0.0
    unique = {tuple(sorted(genome.parameters.items())) for genome in population}
    return round(len(unique) / len(population), 6)


def _select_elites(evaluations: list[FitnessEvaluation], elite_count: int) -> list[Genome]:
    if elite_count <= 0:
        return []
    ranked = sorted(evaluations, key=lambda item: item.fitness, reverse=True)
    return [item.genome for item in ranked[:elite_count]]


def _next_population(
    evaluations: list[FitnessEvaluation],
    config: GAExecutionConfig,
    rng: random.Random,
    generation: int,
) -> list[Genome]:
    elites = _select_elites(evaluations, config.elite_count)
    if not elites:
        return []

    next_population = [
        Genome(genome_id=f"gen{generation:03d}-elite{index:03d}", parameters=dict(genome.parameters))
        for index, genome in enumerate(elites)
    ]
    parent_pool = elites if len(elites) > 1 else [elites[0], elites[0]]

    while len(next_population) < config.population_size:
        parent_a = rng.choice(parent_pool)
        parent_b = rng.choice(parent_pool)
        child_id = f"gen{generation:03d}-ind{len(next_population):03d}"
        if rng.random() < config.crossover_rate:
            child = crossover_genomes(parent_a, parent_b, rng, child_id)
        else:
            child = Genome(genome_id=child_id, parameters=dict(parent_a.parameters))
        child = mutate_genome(child, rng, mutation_rate=config.mutation_rate, genome_id=child_id)
        next_population.append(child)

    return next_population[: config.population_size]


def run_ga_execution(config: GAExecutionConfig, evaluator: MockEvaluator | None = None) -> GAExecutionResult:
    """Run a deterministic mock-first GA loop without invoking any backtest adapter."""

    if config.population_size <= 0:
        raise ValueError("population_size_must_be_positive")
    if config.generations <= 0:
        raise ValueError("generations_must_be_positive")

    rng = random.Random(config.seed)
    resolved_evaluator = evaluator or MockEvaluator(seed=config.seed)
    population = create_population(config.population_size, rng, prefix="gen000")
    results: list[GenerationResult] = []

    for generation in range(1, config.generations + 1):
        evaluations = sorted(
            evaluate_population(population, resolved_evaluator),
            key=lambda item: item.fitness,
            reverse=True,
        )
        best = evaluations[0]
        results.append(
            GenerationResult(
                generation=generation,
                population=population,
                evaluations=evaluations,
                best=best,
                average_fitness=_average_fitness(evaluations),
                diversity=_diversity(population),
            )
        )
        if generation < config.generations:
            population = _next_population(evaluations, config, rng, generation)

    return GAExecutionResult(config=config, generations=results)

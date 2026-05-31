"""Tests for Bollinger Evolver GA population operations."""

from __future__ import annotations

import random
import unittest

from bollinger_evolver.ga import (
    GenerationResult,
    build_next_population,
    crossover_candidates,
    initialize_population,
    mutate_candidate,
    normalize_candidate_genes,
    select_elites,
)
from bollinger_evolver.ga.generation_runner import IndividualEvaluation
from bollinger_evolver.gene_space import GeneDefinition, GeneSpace, load_gene_space, validate_genes
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _generation_result(individuals: list[IndividualEvaluation]) -> GenerationResult:
    return GenerationResult(
        success=True,
        run_id="run-test",
        generation_index=1,
        population_size=len(individuals),
        evaluated_count=len(individuals),
        success_count=len([item for item in individuals if item.success]),
        failure_count=len([item for item in individuals if not item.success]),
        best=next((item for item in individuals if item.success), None),
        individuals=individuals,
    )


def _individual(
    index: int,
    score: float,
    *,
    success: bool = True,
    candidate: dict | None = None,
) -> IndividualEvaluation:
    return IndividualEvaluation(
        index=index,
        candidate_id=f"candidate-{index}",
        success=success,
        fitness_score=score,
        candidate=candidate or {"gene_a": index, "gene_b": float(index), "mode": "hybrid"},
        metrics={"score": score},
        reason=None if success else "failed",
        artifact_path=None,
    )


def _gene_space() -> GeneSpace:
    return {
        "gene_a": GeneDefinition(name="gene_a", gene_type="int", minimum=1, maximum=10),
        "gene_b": GeneDefinition(name="gene_b", gene_type="float", minimum=0.1, maximum=5.0),
        "mode": GeneDefinition(name="mode", gene_type="choice", choices=("hybrid", "breakout")),
        "enabled": GeneDefinition(name="enabled", gene_type="bool"),
    }


class TestSelectElites(unittest.TestCase):
    def test_select_elites_uses_successful_individuals_only(self) -> None:
        result = _generation_result(
            [
                _individual(0, 9.0, success=True),
                _individual(1, 8.0, success=False),
                _individual(2, 7.0, success=True),
            ]
        )

        elites = select_elites(result, 2)

        self.assertEqual(len(elites), 2)
        self.assertEqual(elites[0]["gene_a"], 0)
        self.assertEqual(elites[1]["gene_a"], 2)

    def test_select_elites_zero_count_returns_empty(self) -> None:
        elites = select_elites(_generation_result([_individual(0, 1.0)]), 0)
        self.assertEqual(elites, [])

    def test_select_elites_returns_available_successes_when_insufficient(self) -> None:
        elites = select_elites(_generation_result([_individual(0, 1.0)]), 5)
        self.assertEqual(len(elites), 1)


class TestCrossoverAndMutation(unittest.TestCase):
    def test_crossover_is_deterministic_and_filters_sensitive_fields(self) -> None:
        parent_a = {"gene_a": 1, "gene_b": 1.0, "mode": "hybrid", "api_secret": "abc"}
        parent_b = {"gene_a": 9, "gene_b": 3.0, "mode": "breakout", "token": "xyz"}

        child_one = crossover_candidates(parent_a, parent_b, random.Random(3))
        child_two = crossover_candidates(parent_a, parent_b, random.Random(3))

        self.assertEqual(child_one, child_two)
        self.assertNotIn("api_secret", child_one)
        self.assertNotIn("token", child_one)

    def test_mutate_candidate_rate_zero_keeps_candidate(self) -> None:
        candidate = {"gene_a": 3, "gene_b": 1.5, "mode": "hybrid", "enabled": True}
        mutated = mutate_candidate(candidate, _gene_space(), random.Random(7), 0.0)
        self.assertEqual(mutated, candidate)

    def test_mutate_candidate_rate_one_returns_valid_candidate(self) -> None:
        candidate = {"gene_a": 3, "gene_b": 1.5, "mode": "hybrid", "enabled": True, "wallet": "hidden"}
        mutated = mutate_candidate(candidate, _gene_space(), random.Random(7), 1.0)

        self.assertNotIn("wallet", mutated)
        self.assertIn(mutated["mode"], ("hybrid", "breakout"))
        self.assertTrue(1 <= mutated["gene_a"] <= 10)
        self.assertTrue(0.1 <= mutated["gene_b"] <= 5.0)
        self.assertIn(mutated["enabled"], (True, False))


class TestRealGeneSpaceIntegration(unittest.TestCase):
    def test_normalize_candidate_uses_default_genes_and_validates(self) -> None:
        gene_space = load_gene_space()
        candidate = {"bb_period_15m": 33, "api_secret": "hidden"}

        normalized = normalize_candidate_genes(candidate, gene_space, rng=random.Random(1))

        self.assertEqual(set(normalized.keys()), set(gene_space.keys()))
        self.assertEqual(normalized["bb_period_15m"], 33)
        self.assertEqual(normalized["bb_std_15m"], DEFAULT_GENES["bb_std_15m"])
        self.assertNotIn("api_secret", normalized)
        validate_genes(normalized, gene_space)

    def test_initialize_population_fills_with_seeded_gene_samples(self) -> None:
        gene_space = load_gene_space()
        initial = [{"bb_period_15m": 21}]

        first = initialize_population(initial, gene_space, 3, random.Random(11))
        second = initialize_population(initial, gene_space, 3, random.Random(11))

        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        for genes in first:
            validate_genes(genes, gene_space)

    def test_crossover_with_gene_space_returns_complete_valid_genes(self) -> None:
        gene_space = load_gene_space()
        parent_a = dict(DEFAULT_GENES)
        parent_b = dict(DEFAULT_GENES)
        parent_b["bb_period_15m"] = 55
        parent_b["mode"] = "breakout"

        child = crossover_candidates(parent_a, parent_b, random.Random(5), gene_space=gene_space)

        self.assertEqual(set(child.keys()), set(gene_space.keys()))
        validate_genes(child, gene_space)

    def test_mutate_with_real_gene_space_is_seeded_and_valid(self) -> None:
        gene_space = load_gene_space()
        candidate = dict(DEFAULT_GENES)

        first = mutate_candidate(candidate, gene_space, random.Random(13), 1.0)
        second = mutate_candidate(candidate, gene_space, random.Random(13), 1.0)

        self.assertEqual(first, second)
        validate_genes(first, gene_space)


class TestBuildNextPopulation(unittest.TestCase):
    def test_build_next_population_preserves_elites_and_fills_population(self) -> None:
        individuals = [
            _individual(0, 30.0, candidate={"gene_a": 9, "gene_b": 1.0, "mode": "hybrid", "enabled": True}),
            _individual(1, 20.0, candidate={"gene_a": 5, "gene_b": 2.0, "mode": "breakout", "enabled": False}),
            _individual(2, 10.0, success=False),
        ]
        result = _generation_result(individuals)

        population = build_next_population(
            result,
            _gene_space(),
            population_size=4,
            elite_count=1,
            mutation_rate=0.2,
            crossover_rate=0.8,
            rng=random.Random(11),
        )

        self.assertEqual(len(population), 4)
        self.assertEqual(population[0]["gene_a"], 9)

    def test_build_next_population_returns_empty_when_no_successes(self) -> None:
        result = _generation_result([_individual(0, -1.0, success=False)])
        population = build_next_population(
            result,
            _gene_space(),
            population_size=3,
            elite_count=1,
            mutation_rate=0.2,
            crossover_rate=0.8,
            rng=random.Random(1),
        )
        self.assertEqual(population, [])

    def test_build_next_population_with_real_gene_space_returns_valid_genes(self) -> None:
        gene_space = load_gene_space()
        candidate_a = dict(DEFAULT_GENES)
        candidate_b = dict(DEFAULT_GENES)
        candidate_b["bb_period_15m"] = 45
        result = _generation_result(
            [
                _individual(0, 30.0, candidate=candidate_a),
                _individual(1, 20.0, candidate=candidate_b),
            ]
        )

        population = build_next_population(
            result,
            gene_space,
            population_size=4,
            elite_count=1,
            mutation_rate=0.5,
            crossover_rate=0.8,
            rng=random.Random(21),
        )

        self.assertEqual(len(population), 4)
        for genes in population:
            validate_genes(genes, gene_space)


if __name__ == "__main__":
    unittest.main()

"""Population operations for the Bollinger Evolver GA orchestrator."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, Mapping

from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.gene_space import GeneDefinition, GeneSpace, load_gene_space, repair_genes, sample_genes
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES

if TYPE_CHECKING:
    from bollinger_evolver.ga.generation_runner import GenerationResult


def _sample_mutated_value(definition: Any, rng: random.Random) -> Any:
    if definition.gene_type == "int":
        return rng.randint(int(definition.minimum), int(definition.maximum))
    if definition.gene_type == "float":
        return float(rng.uniform(float(definition.minimum), float(definition.maximum)))
    if definition.gene_type == "bool":
        return rng.choice([True, False])
    if definition.gene_type == "choice":
        return rng.choice(list(definition.choices))
    raise ValueError(f"Unsupported gene type: {definition.gene_type}")


def _value_matches_definition(value: Any, definition: GeneDefinition) -> bool:
    if definition.gene_type == "int":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and int(definition.minimum) <= value <= int(definition.maximum)
        )
    if definition.gene_type == "float":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and float(definition.minimum) <= float(value) <= float(definition.maximum)
        )
    if definition.gene_type == "bool":
        return isinstance(value, bool)
    if definition.gene_type == "choice":
        return value in definition.choices
    return False


def _default_or_sample_gene(
    gene_name: str,
    definition: GeneDefinition,
    rng: random.Random | None,
) -> Any:
    default_value = DEFAULT_GENES.get(gene_name)
    if _value_matches_definition(default_value, definition):
        return default_value
    return _sample_mutated_value(definition, rng or random.Random())


def normalize_candidate_genes(
    candidate: Mapping[str, Any],
    gene_space: GeneSpace,
    *,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Return a complete, sanitized gene snapshot constrained by gene space."""

    sanitized = sanitize_mapping(candidate)
    normalized: dict[str, Any] = {}

    for gene_name, definition in gene_space.items():
        if gene_name in sanitized and _value_matches_definition(sanitized[gene_name], definition):
            normalized[gene_name] = sanitized[gene_name]
        else:
            normalized[gene_name] = _default_or_sample_gene(gene_name, definition, rng)

    return repair_genes(normalized, gene_space)


def extract_gene_snapshot(
    candidate: Mapping[str, Any],
    gene_space: GeneSpace | None = None,
) -> dict[str, Any]:
    """Extract only gene-space fields from a mixed candidate/metadata payload."""

    resolved_gene_space = gene_space or load_gene_space()
    sanitized = sanitize_mapping(candidate)
    return {
        gene_name: sanitized[gene_name]
        for gene_name in resolved_gene_space.keys()
        if gene_name in sanitized
    }


def initialize_population(
    initial_population: list[dict[str, Any]],
    gene_space: GeneSpace,
    population_size: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Normalize provided candidates and fill the population with sampled genes."""

    if population_size <= 0 or not initial_population:
        return []

    population: list[dict[str, Any]] = []
    for candidate in initial_population[:population_size]:
        if isinstance(candidate, Mapping):
            population.append(normalize_candidate_genes(candidate, gene_space, rng=rng))

    while len(population) < population_size:
        sampled = dict(DEFAULT_GENES)
        sampled.update(sample_genes(gene_space, rng=rng))
        population.append(normalize_candidate_genes(sampled, gene_space, rng=rng))

    return population


def select_elites(generation_result: GenerationResult, elite_count: int) -> list[dict[str, Any]]:
    """Select top successful candidates from a generation result."""

    if elite_count <= 0:
        return []

    successful = [item for item in generation_result.individuals if item.success]
    return [sanitize_mapping(item.candidate) for item in successful[:elite_count]]


def crossover_candidates(
    parent_a: Mapping[str, Any],
    parent_b: Mapping[str, Any],
    rng: random.Random,
    gene_space: GeneSpace | None = None,
) -> dict[str, Any]:
    """Create one child by mixing sanitized parent values per key."""

    sanitized_a = (
        normalize_candidate_genes(parent_a, gene_space, rng=rng)
        if gene_space is not None
        else sanitize_mapping(parent_a)
    )
    sanitized_b = (
        normalize_candidate_genes(parent_b, gene_space, rng=rng)
        if gene_space is not None
        else sanitize_mapping(parent_b)
    )
    child: dict[str, Any] = {}
    keys = list(gene_space.keys()) if gene_space is not None else sorted(set(sanitized_a.keys()) | set(sanitized_b.keys()))
    for key in keys:
        if key in sanitized_a and key in sanitized_b:
            child[key] = sanitized_a[key] if rng.random() < 0.5 else sanitized_b[key]
        elif key in sanitized_a:
            child[key] = sanitized_a[key]
        else:
            child[key] = sanitized_b[key]
    return normalize_candidate_genes(child, gene_space, rng=rng) if gene_space is not None else child


def mutate_candidate(
    candidate: Mapping[str, Any],
    gene_space: GeneSpace,
    rng: random.Random,
    mutation_rate: float,
) -> dict[str, Any]:
    """Mutate genes in-place according to the provided gene space."""

    sanitized = normalize_candidate_genes(candidate, gene_space, rng=rng)
    if mutation_rate <= 0.0:
        return repaired_candidate(sanitized, gene_space)

    mutated = dict(sanitized)
    for gene_name, definition in gene_space.items():
        if gene_name not in mutated:
            mutated[gene_name] = _sample_mutated_value(definition, rng)
            continue
        if rng.random() < mutation_rate:
            mutated[gene_name] = _sample_mutated_value(definition, rng)
    return repaired_candidate(mutated, gene_space)


def repaired_candidate(candidate: Mapping[str, Any], gene_space: GeneSpace) -> dict[str, Any]:
    return normalize_candidate_genes(repair_genes(candidate, gene_space), gene_space)


def build_next_population(
    generation_result: GenerationResult,
    gene_space: GeneSpace,
    population_size: int,
    elite_count: int,
    mutation_rate: float,
    crossover_rate: float,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Construct the next population from successful individuals only."""

    if population_size <= 0:
        return []

    successful_pool = [
        normalize_candidate_genes(item.candidate, gene_space, rng=rng)
        for item in generation_result.individuals
        if item.success
    ]
    if not successful_pool:
        return []

    elites = select_elites(generation_result, elite_count)[:population_size]
    next_population = [
        normalize_candidate_genes(candidate, gene_space, rng=rng)
        for candidate in elites
    ]

    while len(next_population) < population_size:
        if len(successful_pool) == 1:
            child = dict(successful_pool[0])
        else:
            parent_a = rng.choice(successful_pool)
            parent_b = rng.choice(successful_pool)
            if rng.random() < crossover_rate:
                child = crossover_candidates(parent_a, parent_b, rng, gene_space=gene_space)
            else:
                child = dict(parent_a)
        child = mutate_candidate(child, gene_space, rng, mutation_rate)
        next_population.append(child)

    return next_population[:population_size]

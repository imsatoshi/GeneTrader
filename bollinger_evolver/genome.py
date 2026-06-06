"""Genome primitives for the lightweight Bollinger GA execution framework."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping

GenomeValue = int | float
GenomeParameters = dict[str, GenomeValue]


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    kind: str
    minimum: float
    maximum: float


GENOME_PARAMETER_SPACE: dict[str, ParameterSpec] = {
    "bb_window": ParameterSpec("bb_window", "int", 10, 80),
    "bb_stddev": ParameterSpec("bb_stddev", "float", 1.2, 3.5),
    "stop_loss_pct": ParameterSpec("stop_loss_pct", "float", 0.01, 0.20),
    "take_profit_pct": ParameterSpec("take_profit_pct", "float", 0.01, 0.50),
    "leverage": ParameterSpec("leverage", "float", 1.0, 10.0),
    "risk_per_trade": ParameterSpec("risk_per_trade", "float", 0.001, 0.05),
}


@dataclass(frozen=True)
class Genome:
    genome_id: str
    parameters: GenomeParameters


def _sample_parameter(spec: ParameterSpec, rng: random.Random) -> GenomeValue:
    if spec.kind == "int":
        return rng.randint(int(spec.minimum), int(spec.maximum))
    if spec.kind == "float":
        return round(rng.uniform(spec.minimum, spec.maximum), 6)
    raise ValueError(f"unsupported_parameter_kind: {spec.kind}")


def _coerce_parameter(value: GenomeValue, spec: ParameterSpec) -> GenomeValue:
    numeric = float(value)
    clipped = max(spec.minimum, min(spec.maximum, numeric))
    if spec.kind == "int":
        return int(round(clipped))
    return round(clipped, 6)


def validate_genome(genome: Genome, parameter_space: Mapping[str, ParameterSpec] | None = None) -> None:
    """Raise ValueError when a genome is incomplete or outside parameter bounds."""

    space = parameter_space or GENOME_PARAMETER_SPACE
    expected = set(space)
    actual = set(genome.parameters)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"invalid_genome_parameters: missing={missing}, unknown={unknown}")

    for name, spec in space.items():
        value = genome.parameters[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"invalid_genome_value_type: {name}")
        numeric = float(value)
        if not spec.minimum <= numeric <= spec.maximum:
            raise ValueError(f"genome_value_out_of_range: {name}")
        if spec.kind == "int" and not isinstance(value, int):
            raise ValueError(f"invalid_genome_int_value: {name}")


def create_random_genome(
    rng: random.Random,
    genome_id: str,
    parameter_space: Mapping[str, ParameterSpec] | None = None,
) -> Genome:
    """Create one random genome constrained by the parameter space."""

    space = parameter_space or GENOME_PARAMETER_SPACE
    genome = Genome(
        genome_id=genome_id,
        parameters={name: _sample_parameter(spec, rng) for name, spec in space.items()},
    )
    validate_genome(genome, space)
    return genome


def create_population(
    population_size: int,
    rng: random.Random,
    *,
    prefix: str = "genome",
    parameter_space: Mapping[str, ParameterSpec] | None = None,
) -> list[Genome]:
    """Create a seeded population of bounded Bollinger strategy genomes."""

    if population_size <= 0:
        return []
    return [
        create_random_genome(rng, f"{prefix}-{index:03d}", parameter_space)
        for index in range(population_size)
    ]


def crossover_genomes(parent_a: Genome, parent_b: Genome, rng: random.Random, child_id: str) -> Genome:
    """Mix parent parameters into one child genome."""

    validate_genome(parent_a)
    validate_genome(parent_b)
    parameters: GenomeParameters = {}
    for name in GENOME_PARAMETER_SPACE:
        parameters[name] = parent_a.parameters[name] if rng.random() < 0.5 else parent_b.parameters[name]
    child = Genome(genome_id=child_id, parameters=parameters)
    validate_genome(child)
    return child


def mutate_genome(
    genome: Genome,
    rng: random.Random,
    *,
    mutation_rate: float,
    genome_id: str | None = None,
) -> Genome:
    """Return a mutated genome while keeping every parameter inside bounds."""

    validate_genome(genome)
    bounded_rate = max(0.0, min(1.0, mutation_rate))
    parameters = dict(genome.parameters)
    for name, spec in GENOME_PARAMETER_SPACE.items():
        if rng.random() < bounded_rate:
            if spec.kind == "int":
                delta = rng.choice([-2, -1, 1, 2])
                parameters[name] = _coerce_parameter(int(parameters[name]) + delta, spec)
            else:
                span = spec.maximum - spec.minimum
                delta = rng.uniform(-0.12 * span, 0.12 * span)
                parameters[name] = _coerce_parameter(float(parameters[name]) + delta, spec)

    mutated = Genome(genome_id=genome_id or genome.genome_id, parameters=parameters)
    validate_genome(mutated)
    return mutated

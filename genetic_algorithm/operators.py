"""Genetic algorithm operators for crossover, mutation, and selection."""
import random
from typing import List, Tuple, Dict, Any

from genetic_algorithm.individual import Individual


def crossover(parent1: Individual, parent2: Individual,
              with_pair: bool = True) -> Tuple[Individual, Individual]:
    """
    Perform single-point crossover between two parents.

    Args:
        parent1: First parent individual
        parent2: Second parent individual
        with_pair: Whether to also crossover trading pairs

    Returns:
        Tuple of two child individuals
    """
    if len(parent1.genes) < 2:
        # Can't crossover with less than 2 genes
        return parent1.copy(), parent2.copy()

    # Crossover genes at random point
    point = random.randint(1, len(parent1.genes) - 1)
    child1_genes = parent1.genes[:point] + parent2.genes[point:]
    child2_genes = parent2.genes[:point] + parent1.genes[point:]

    # Crossover trading pairs
    if with_pair and parent1.trading_pairs and parent2.trading_pairs:
        all_pairs = list(set(parent1.trading_pairs + parent2.trading_pairs))
        random.shuffle(all_pairs)

        child1_pairs = all_pairs[:len(parent1.trading_pairs)]
        child2_pairs = all_pairs[:len(parent2.trading_pairs)]

        return (
            Individual(child1_genes, child1_pairs, parent1.param_types),
            Individual(child2_genes, child2_pairs, parent2.param_types)
        )

    return (
        Individual(child1_genes, parent1.trading_pairs.copy(), parent1.param_types),
        Individual(child2_genes, parent2.trading_pairs.copy(), parent2.param_types)
    )


def mutate(individual: Individual, mutation_rate: float) -> None:
    """
    Apply mutation to an individual's genes.

    Supports multiple mutation strategies:
    - noise: Add Gaussian noise to numeric values
    - reset: Reset to random value within range
    - scale: Scale value by random factor

    Args:
        individual: Individual to mutate (modified in place)
        mutation_rate: Probability of mutating each gene
    """
    for i in range(len(individual.genes)):
        if random.random() >= mutation_rate:
            continue

        param_type = individual.param_types[i]

        # Handle dictionary-style parameter types
        if isinstance(param_type, dict) and 'type' in param_type:
            _mutate_typed_gene(individual, i, param_type)
        # Handle boolean genes
        elif isinstance(individual.genes[i], bool):
            individual.genes[i] = not individual.genes[i]
        # Handle categorical/list genes
        elif isinstance(param_type, dict) and 'options' in param_type:
            individual.genes[i] = random.choice(param_type['options'])


def _mutate_typed_gene(individual: Individual, index: int, param_type: Dict[str, Any]) -> None:
    """
    Apply mutation to a typed gene (Int, Decimal, Boolean, Categorical).

    Args:
        individual: Individual being mutated
        index: Index of the gene to mutate
        param_type: Parameter type definition
    """
    gene_type = param_type['type']

    if gene_type == 'Boolean':
        individual.genes[index] = not individual.genes[index]
        return

    if gene_type == 'Categorical':
        options = param_type.get('options', [])
        if options:
            individual.genes[index] = random.choice(options)
        return

    # Numeric types: Int or Decimal
    if gene_type not in ('Int', 'Decimal'):
        return

    mutation_strategy = random.choice(['noise', 'reset', 'scale'])
    start = param_type.get('start', 0)
    end = param_type.get('end', 100)
    decimal_places = param_type.get('decimal_places', 2)

    if mutation_strategy == 'noise':
        # Add Gaussian noise
        noise_scale = (end - start) * 0.1
        noise = random.gauss(0, noise_scale)
        new_value = individual.genes[index] + noise

    elif mutation_strategy == 'reset':
        # Reset to random value
        if gene_type == 'Int':
            individual.genes[index] = random.randint(int(start), int(end))
            return
        else:
            new_value = random.uniform(start, end)

    else:  # scale
        # Scale by random factor
        scale_factor = random.uniform(0.8, 1.2)
        new_value = individual.genes[index] * scale_factor

    # Clamp to valid range
    new_value = max(start, min(end, new_value))

    # Apply type-specific formatting
    if gene_type == 'Int':
        individual.genes[index] = int(round(new_value))
    else:
        individual.genes[index] = round(new_value, decimal_places)


def select_tournament(population: List[Individual], tournament_size: int) -> Individual:
    """
    Select an individual using tournament selection.

    Args:
        population: List of individuals to select from
        tournament_size: Number of individuals in tournament

    Returns:
        Individual with highest fitness from tournament

    Raises:
        ValueError: If population is empty or tournament_size is invalid
    """
    if not population:
        raise ValueError("Cannot select from empty population")

    tournament_size = min(tournament_size, len(population))
    tournament = random.sample(population, tournament_size)

    return max(tournament, key=lambda ind: ind.fitness if ind.fitness is not None else float('-inf'))

"""Population management for genetic algorithm."""
from typing import List, Dict, Optional
from genetic_algorithm.individual import Individual


class Population:
    """A collection of individuals in the genetic algorithm."""

    def __init__(self, individuals: List[Individual]):
        """Initialize population with a list of individuals.

        Args:
            individuals: List of Individual objects
        """
        self.individuals = individuals

    @classmethod
    def create_random(cls, size: int, parameters: Dict, trading_pairs: List[str],
                      num_pairs: Optional[int]) -> 'Population':
        """Create a population of random individuals.

        Args:
            size: Number of individuals to create
            parameters: Parameter definitions for individuals
            trading_pairs: Available trading pairs
            num_pairs: Number of pairs per individual (None for all pairs)

        Returns:
            New Population instance with random individuals
        """
        return cls([Individual.create_random(parameters, trading_pairs, num_pairs) for _ in range(size)])

    def get_best(self) -> Individual:
        """Get the individual with the highest fitness.

        Returns:
            Individual with highest fitness score

        Raises:
            ValueError: If population is empty
        """
        if not self.individuals:
            raise ValueError("Cannot get best from empty population")
        return max(self.individuals, key=lambda ind: ind.fitness if ind.fitness is not None else float('-inf'))

    def __len__(self) -> int:
        """Return the number of individuals in the population."""
        return len(self.individuals)

    def __iter__(self):
        """Iterate over individuals in the population."""
        return iter(self.individuals)

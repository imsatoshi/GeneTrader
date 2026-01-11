"""Base optimizer abstract class for strategy optimization."""
from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Dict
from genetic_algorithm.individual import Individual


class BaseOptimizer(ABC):
    """Abstract base class for all optimizers."""

    def __init__(self, settings: Any, parameters: List[Dict]):
        """
        Initialize the optimizer.

        Args:
            settings: Settings object containing optimization configuration
            parameters: List of parameter definitions for optimization
        """
        self.settings = settings
        self.parameters = parameters

    @abstractmethod
    def optimize(self, initial_individuals: List[Individual] = None) -> List[Tuple[int, Individual]]:
        """
        Run the optimization process.

        Args:
            initial_individuals: Optional list of initial individuals to seed the optimization

        Returns:
            List of tuples containing (generation/trial number, best individual)
        """
        pass

    @abstractmethod
    def get_best_individual(self) -> Individual:
        """
        Get the best individual found during optimization.

        Returns:
            The best Individual found
        """
        pass

"""Genetic algorithm optimizer wrapper for strategy optimization.

This module wraps the existing genetic algorithm implementation
into the unified optimizer interface.
"""
import gc
import random
import multiprocessing
from typing import List, Tuple, Any, Dict, Optional

from optimization.base_optimizer import BaseOptimizer
from genetic_algorithm.individual import Individual
from genetic_algorithm.population import Population
from genetic_algorithm.operators import crossover, mutate, select_tournament
from strategy.backtest import run_backtest
from utils.logging_config import logger


class GeneticOptimizer(BaseOptimizer):
    """
    Genetic algorithm optimizer using selection, crossover, and mutation.

    This is the original optimization method, suitable for exploring
    diverse solution spaces with potentially multiple local optima.
    """

    def __init__(self, settings: Any, parameters: List[Dict], all_pairs: List[str]):
        """
        Initialize the genetic optimizer.

        Args:
            settings: Settings object containing optimization configuration
            parameters: List of parameter definitions for optimization
            all_pairs: List of all available trading pairs
        """
        super().__init__(settings, parameters)
        self.all_pairs = all_pairs
        self.best_individual: Optional[Individual] = None

    def _create_population(self, population_size: int, initial_individuals: List[Individual] = None) -> Population:
        """
        Create initial population.

        Args:
            population_size: Size of the population to create
            initial_individuals: Optional list of individuals to include

        Returns:
            Population object
        """
        population = Population.create_random(
            size=population_size,
            parameters=self.parameters,
            trading_pairs=self.all_pairs,
            num_pairs=None if self.settings.fix_pairs else self.settings.num_pairs
        )

        if initial_individuals:
            population.individuals.extend(initial_individuals)

        return population

    def optimize(self, initial_individuals: List[Individual] = None) -> List[Tuple[int, Individual]]:
        """
        Run genetic algorithm optimization.

        Args:
            initial_individuals: Optional list of initial individuals to seed the population

        Returns:
            List of tuples containing (generation number, best individual)
        """
        # Calculate population size accounting for initial individuals
        population_size = self.settings.population_size - len(initial_individuals or [])
        population = self._create_population(population_size, initial_individuals)

        best_individuals = []

        with multiprocessing.Pool(processes=self.settings.pool_processes) as pool:
            for gen in range(self.settings.generations):
                logger.info(f"Generation {gen+1}")

                # Evaluate fitness in parallel
                try:
                    fitnesses = pool.starmap(
                        run_backtest,
                        [(ind.genes, ind.trading_pairs, gen+1) for ind in population.individuals]
                    )

                    for ind, fit in zip(population.individuals, fitnesses):
                        ind.fitness = fit if fit is not None else float('-inf')

                except Exception as e:
                    logger.error(f"Error during fitness calculation in generation {gen+1}: {str(e)}")

                # Filter out individuals with None fitness
                valid_individuals = [ind for ind in population.individuals if ind.fitness is not None]
                logger.info(f"Valid individuals in generation {gen+1}: {len(valid_individuals)}")

                if not valid_individuals:
                    logger.warning(f"No valid individuals in generation {gen+1}. Terminating early.")
                    break

                # Select individuals for the next generation
                offspring = [
                    select_tournament(valid_individuals, self.settings.tournament_size)
                    for _ in range(self.settings.population_size)
                ]

                # Apply crossover
                for i in range(0, len(offspring), 2):
                    if random.random() < self.settings.crossover_prob:
                        offspring[i], offspring[i+1] = crossover(
                            offspring[i],
                            offspring[i+1],
                            with_pair=self.settings.fix_pairs
                        )
                        offspring[i].after_genetic_operation(self.parameters)
                        offspring[i+1].after_genetic_operation(self.parameters)

                # Apply mutation
                for ind in offspring:
                    mutate(ind, self.settings.mutation_prob)
                    ind.after_genetic_operation(self.parameters)

                # Replace the population
                population.individuals = offspring

                # Find the best individual in the current generation
                best_individual = max(valid_individuals, key=lambda ind: ind.fitness)
                best_individuals.append((gen+1, best_individual))

                # Update overall best
                if self.best_individual is None or best_individual.fitness > self.best_individual.fitness:
                    self.best_individual = best_individual

                logger.info(f"Best individual in generation {gen+1}: Fitness: {best_individual.fitness}")

                gc.collect()  # Clean up memory at the end of each generation

        return best_individuals

    def get_best_individual(self) -> Individual:
        """
        Get the best individual found during optimization.

        Returns:
            The best Individual found
        """
        return self.best_individual

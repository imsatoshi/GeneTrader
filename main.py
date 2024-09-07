import argparse
import json
import time
from typing import List
import multiprocessing
import random

from config.settings import Settings
from utils.logging_config import logger
from utils.file_operations import create_directories
from genetic_algorithm.individual import Individual
from genetic_algorithm.population import Population
from genetic_algorithm.operators import crossover, mutate, select_tournament
from strategy.backtest import run_backtest

def genetic_algorithm(settings: Settings) -> List[tuple[int, Individual]]:
    population = Population.create_random(settings.population_size)
    best_individuals = []

    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(settings.generations):
            logger.info(f"Generation {gen+1}")
            
            # Evaluate fitness in parallel
            fitnesses = pool.starmap(run_backtest, [(ind.genes, gen+1) for ind in population.individuals])
            for ind, fit in zip(population.individuals, fitnesses):
                ind.fitness = fit

            # Select individuals for the next generation
            offspring = [select_tournament(population.individuals, settings.tournament_size) for _ in range(settings.population_size)]

            # Apply crossover and mutation
            for i in range(0, len(offspring), 2):
                if random.random() < settings.crossover_prob:
                    offspring[i], offspring[i+1] = crossover(offspring[i], offspring[i+1])

            for ind in offspring:
                mutate(ind, settings.mutation_prob)

            # Replace the population
            population.individuals = offspring

            # Find the best individual in the current generation
            best_ind = population.get_best()
            best_individuals.append((gen+1, best_ind))

            logger.info(f"Best individual in generation {gen+1}: Fitness: {best_ind.fitness}")

    return best_individuals

def save_best_individual(individual: Individual, generation: int, settings: Settings):
    filename = f"{settings.best_generations_dir}/best_individual_gen{generation}.json"
    data = {
        'generation': generation,
        'fitness': individual.fitness,
        'genes': individual.genes
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved best individual from generation {generation} to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Run genetic algorithm for trading strategy optimization')
    parser.add_argument('--config', type=str, default='ga.json', help='Path to the configuration file')
    args = parser.parse_args()

    try:
        # Initialize settings
        settings = Settings(args.config)

        # Create necessary directories
        create_directories([settings.results_dir, settings.best_generations_dir])

        # Record start time
        start_time = time.time()

        # Run genetic algorithm
        best_individuals = genetic_algorithm(settings)

        # Save best individuals
        for gen, ind in best_individuals:
            save_best_individual(ind, gen, settings)

        # Record end time and calculate duration
        end_time = time.time()
        duration = end_time - start_time

        # Log overall best individual
        overall_best = max(best_individuals, key=lambda x: x[1].fitness)
        logger.info(f"Overall best individual: Generation {overall_best[0]}, Fitness: {overall_best[1].fitness}")
        logger.info(f"Genetic algorithm completed successfully in {duration:.2f} seconds")

    except Exception as e:
        logger.exception(f"An error occurred during the execution of the genetic algorithm: {str(e)}")

if __name__ == "__main__":
    main()
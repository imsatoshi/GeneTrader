import argparse
import json
import time
from typing import List
import multiprocessing
import random
from datetime import datetime, date
import os
from config.settings import Settings
from utils.logging_config import logger
from utils.file_operations import create_directories
from genetic_algorithm.individual import Individual
from genetic_algorithm.population import Population
from genetic_algorithm.operators import crossover, mutate, select_tournament
from strategy.backtest import run_backtest
from data.downloader import download_data  
from strategy.gen_template import generate_dynamic_template


def load_trading_pairs(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config['exchange']['pair_whitelist']

def crossover_trading_pairs(parent1: Individual, parent2: Individual, num_pairs: int):
    all_pairs = list(set(parent1.trading_pairs + parent2.trading_pairs))
    if len(all_pairs) > num_pairs:
        return random.sample(all_pairs, num_pairs)
    else:
        return all_pairs

def genetic_algorithm(settings: Settings, initial_individuals: List[Individual] = None) -> List[tuple[int, Individual]]:
    # Load trading pairs
    all_pairs = load_trading_pairs(settings.config_file)
    
    print(settings.parameters)
    print(all_pairs)
    print(settings.num_pairs)

    # Create initial population with random individuals and add initial_individuals
    population = Population.create_random(
        settings.population_size - len(initial_individuals or []),
        settings.parameters,
        all_pairs,
        settings.num_pairs
    )
    if initial_individuals:
        population.individuals.extend(initial_individuals)
    
    best_individuals = []

    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(settings.generations):
            logger.info(f"Generation {gen+1}")
            
            # Evaluate fitness in parallel
            fitnesses = pool.starmap(run_backtest, [(ind.genes, ind.trading_pairs, gen+1) for ind in population.individuals])
            for ind, fit in zip(population.individuals, fitnesses):
                ind.fitness = fit

            # Filter out individuals with None fitness
            valid_individuals = [ind for ind in population.individuals if ind.fitness is not None]
            
            if not valid_individuals:
                logger.warning(f"No valid individuals in generation {gen+1}. Terminating early.")
                break

            # Select individuals for the next generation
            offspring = [select_tournament(valid_individuals, settings.tournament_size) for _ in range(settings.population_size)]

            # Apply crossover and mutation
            for i in range(0, len(offspring), 2):
                if random.random() < settings.crossover_prob:
                    offspring[i], offspring[i+1] = crossover(offspring[i], offspring[i+1])
                    # Crossover trading pairs
                    offspring[i].trading_pairs = crossover_trading_pairs(offspring[i], offspring[i+1], settings.num_pairs)
                    offspring[i+1].trading_pairs = crossover_trading_pairs(offspring[i], offspring[i+1], settings.num_pairs)
                    offspring[i].after_genetic_operation(settings.parameters)
                    offspring[i+1].after_genetic_operation(settings.parameters)

            for ind in offspring:
                mutate(ind, settings.mutation_prob)
                # Mutate trading pairs
                ind.mutate_trading_pairs(all_pairs, settings.mutation_prob)
                ind.after_genetic_operation(settings.parameters)

            # Replace the population
            population.individuals = offspring

            # Find the best individual in the current generation
            best_ind = max(valid_individuals, key=lambda ind: ind.fitness)
            best_individuals.append((gen+1, best_ind))

            logger.info(f"Best individual in generation {gen+1}: Fitness: {best_ind.fitness}")

    return best_individuals

def save_best_individual(individual: Individual, generation: int, settings: Settings):
    filename = f"{settings.best_generations_dir}/best_individual_gen{generation}.json"
    data = {
        'generation': generation,
        'fitness': individual.fitness,
        'genes': individual.genes,
        'trading_pairs': individual.trading_pairs
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved best individual from generation {generation} to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Run genetic algorithm for trading strategy optimization')
    parser.add_argument('--config', type=str, default='ga.json', help='Path to the configuration file')
    parser.add_argument('--download', action='store_true', help='Download data before running the algorithm')
    parser.add_argument('--start-date', type=str, default='20240101', help='Start date for data download (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, default=date.today().strftime('%Y%m%d'), help='End date for data download (YYYYMMDD)')
    args = parser.parse_args()

    try:
        # Initialize settings
        settings = Settings(args.config)

        # Generate dynamic template and get parameters
        _, parameters = generate_dynamic_template(settings.base_strategy_file)

        # Update parameters in settings
        settings.parameters = parameters

        # Create necessary directories
        create_directories([settings.results_dir, settings.best_generations_dir])

        # Download data if requested
        if args.download:
            start_date = datetime.strptime(args.start_date, '%Y%m%d').date()
            end_date = datetime.strptime(args.end_date, '%Y%m%d').date()
            logger.info(f"Downloading data from {start_date} to {end_date}")
            download_data(start_date, end_date)

        # Record start time
        start_time = time.time()

        # Run genetic algorithm
        # Initial individuals (now including trading pairs)
        all_pairs = load_trading_pairs(settings.config_file)
        initial_individuals = [
        ]

        best_individuals = genetic_algorithm(settings, initial_individuals)

        # Save best individuals
        for gen, ind in best_individuals:
            save_best_individual(ind, gen, settings)

        # Record end time and calculate duration
        end_time = time.time()
        duration = end_time - start_time

        # Log overall best individual
        overall_best = max(best_individuals, key=lambda x: x[1].fitness)
        logger.info(f"Overall best individual: Generation {overall_best[0]}, Fitness: {overall_best[1].fitness}")
        logger.info(f"Best trading pairs: {overall_best[1].trading_pairs}")
        logger.info(f"Genetic algorithm completed successfully in {duration:.2f} seconds")

    except Exception as e:
        logger.exception(f"An error occurred during the execution of the genetic algorithm: {str(e)}")

if __name__ == "__main__":
    main()

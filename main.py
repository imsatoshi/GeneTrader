import argparse
import json
import time
from typing import List
import multiprocessing
import random
from datetime import datetime, date
import os
import pickle
import numpy as np
from config.settings import Settings
from config.config import LOG_CONFIG
from utils.logging_config import logger
from utils.file_operations import create_directories
from genetic_algorithm.individual import Individual
from genetic_algorithm.population import Population
from genetic_algorithm.operators import crossover, mutate, select_tournament
from strategy.backtest import run_backtest
from data.downloader import download_data  
from strategy.gen_template import generate_dynamic_template
import asyncio
import gzip
import gc


def load_trading_pairs(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config['exchange']['pair_whitelist']


def create_population(settings, all_pairs, population_size, initial_individuals=None):
    population = Population.create_random(
        size=population_size,
        parameters=settings.parameters,
        trading_pairs=all_pairs,
        num_pairs=None if settings.fix_pairs else settings.num_pairs
    )
    if initial_individuals:
        population.individuals.extend(initial_individuals)
    return population

def genetic_algorithm(settings: Settings, initial_individuals: List[Individual] = None) -> List[tuple[int, Individual]]:
    all_pairs = load_trading_pairs(settings.config_file)
    
    # Load the latest checkpoint if it exists
    population_size = settings.population_size - len(initial_individuals or [])
    population = create_population(settings, all_pairs, population_size, initial_individuals)
    
    best_individuals = []
    # print(all_pairs)
    all_pairs_array = np.array(all_pairs)
    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(settings.generations):
            logger.info(f"Generation {gen+1}")
                        
            # Evaluate fitness in parallel
            try:
                fitnesses = pool.starmap(run_backtest, 
                    [(ind.genes, all_pairs_array[ind.trading_pairs_index].tolist(), gen+1) for ind in population.individuals])
                
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
            offspring = [select_tournament(valid_individuals, settings.tournament_size) for _ in range(settings.population_size)]

            # Apply crossover and mutation
            for i in range(0, len(offspring), 2):
                if random.random() < settings.crossover_prob:
                    offspring[i], offspring[i+1] = crossover(offspring[i], offspring[i+1], with_pair=settings.fix_pairs)                    
                    offspring[i].after_genetic_operation(settings.parameters)
                    offspring[i+1].after_genetic_operation(settings.parameters)
            
            for ind in offspring:
                mutate(ind, settings.mutation_prob, all_pairs)  # 使用设定的突变概率
                ind.after_genetic_operation(settings.parameters)

            # Replace the population
            population.individuals = offspring

            # Find the best individual in the current generation
            best_individual = max(valid_individuals, key=lambda ind: ind.fitness)
            best_individuals.append((gen+1, best_individual))

            logger.info(f"Best individual in generation {gen+1}: Fitness: {best_individual.fitness}")

            gc.collect()  # Clean up memory at the end of each generation

    return best_individuals

def save_best_individual(individual: Individual, generation: int, settings: Settings, all_pairs_array: np.array):
    filename = f"{settings.best_generations_dir}/best_individual_gen{generation}.json"
    data = {
        'generation': generation,
        'fitness': individual.fitness,
        'genes': individual.genes,
        'trading_pairs': all_pairs_array[individual.trading_pairs_index].tolist()
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
    parser.add_argument('--resume', action='store_true', help='Resume from the latest checkpoint')
    args = parser.parse_args()

    settings = Settings(args.config)

    try:
        all_pairs = load_trading_pairs(settings.config_file)
        all_pairs_array = np.array(all_pairs)

        # Initialize settings

        # Generate dynamic template and get parameters
        _, parameters = generate_dynamic_template(settings.base_strategy_file)
        settings.parameters = parameters

        # Create all necessary directories including logs
        create_directories([
            settings.results_dir, 
            settings.best_generations_dir, 
            settings.checkpoint_dir,
            LOG_CONFIG['log_dir']
        ])

        # Download data if requested
        if args.download:
            start_date = datetime.strptime(args.start_date, '%Y%m%d').date()
            logger.info(f"Downloading data from {start_date}")
            download_data(start_date)

        # Run genetic algorithm
        best_individuals = genetic_algorithm(settings)

        # Save best individuals
        for gen, ind in best_individuals:
            save_best_individual(ind, gen, settings, all_pairs_array)

        # Log overall best individual
        overall_best = max(best_individuals, key=lambda x: x[1].fitness)
        logger.info(f"Overall best individual: Generation {overall_best[0]}, Fitness: {overall_best[1].fitness}")
    
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
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
from data.downloader import download_data  # 假设您有一个数据下载模块
from strategy.gen_template import generate_dynamic_template

def genetic_algorithm(settings: Settings, initial_individuals: List[Individual] = None) -> List[tuple[int, Individual]]:
    # Create initial population with random individuals and add initial_individuals
    population = Population.create_random(
        settings.population_size - len(initial_individuals or []),
        settings.parameters
    )
    if initial_individuals:
        population.individuals.extend(initial_individuals)
    
    best_individuals = []

    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(settings.generations):
            logger.info(f"Generation {gen+1}")
            
            # Evaluate fitness in parallel
            fitnesses = pool.starmap(run_backtest, [(ind.genes, gen+1) for ind in population.individuals])
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
                    # 修改这里，传入 settings.parameters
                    offspring[i].after_genetic_operation(settings.parameters)
                    offspring[i+1].after_genetic_operation(settings.parameters)

            for ind in offspring:
                mutate(ind, settings.mutation_prob)
                # 修改这里，传入 settings.parameters
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
        'genes': individual.genes
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

        # 生成动态模板并获取参数
        _, parameters = generate_dynamic_template(settings.base_strategy_file)

        # 更新 settings 中的参数
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
        # Initial individuals
        initial_individuals = [
            Individual([66, 17, 0.935, 0.51, 60, 3, -0.01]),
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
        logger.info(f"Genetic algorithm completed successfully in {duration:.2f} seconds")

    except Exception as e:
        logger.exception(f"An error occurred during the execution of the genetic algorithm: {str(e)}")

if __name__ == "__main__":
    main()
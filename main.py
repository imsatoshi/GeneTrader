import argparse
import json
import time
from typing import List
import multiprocessing
import random
from datetime import datetime, date
import os
import pickle
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


def crossover_trading_pairs(parent1: Individual, parent2: Individual, num_pairs: int):
    all_pairs = list(set(parent1.trading_pairs + parent2.trading_pairs))
    if len(all_pairs) > num_pairs:
        return random.sample(all_pairs, num_pairs)
    else:
        return all_pairs


async def save_checkpoint_async(population, generation, settings):
    checkpoint = {
        'generation': generation,
        'individuals': [
            {
                'genes': ind.genes,
                'trading_pairs': ind.trading_pairs,
                'fitness': ind.fitness
            } for ind in population.individuals
        ]
    }
    filename = f"{settings.checkpoint_dir}/checkpoint_gen{generation}.pkl.gz"
    
    def save_to_file():
        with gzip.open(filename, 'wb') as f:
            pickle.dump(checkpoint, f)
    
    await asyncio.get_event_loop().run_in_executor(None, save_to_file)
    logger.info(f"Saved compressed checkpoint for generation {generation}")


def save_checkpoint(population, generation, settings):
    asyncio.run(save_checkpoint_async(population, generation, settings))


def load_latest_checkpoint(settings):
    checkpoints = [f for f in os.listdir(settings.checkpoint_dir) if f.endswith('.pkl.gz')]
    if not checkpoints:
        return None, 0
    latest_checkpoint = max(checkpoints, key=lambda x: int(x.split('gen')[1].split('.')[0]))
    filename = f"{settings.checkpoint_dir}/{latest_checkpoint}"
    
    with gzip.open(filename, 'rb') as f:
        checkpoint = pickle.load(f)
    
    population = Population([])
    for ind_data in checkpoint['individuals']:
        individual = Individual(ind_data['genes'], ind_data['trading_pairs'])
        individual.fitness = ind_data['fitness']
        population.individuals.append(individual)
    
    logger.info(f"Loaded compressed checkpoint from generation {checkpoint['generation']}")
    return population, checkpoint['generation']


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
    population, start_generation = load_latest_checkpoint(settings)
    if population is None:
        population_size = settings.population_size - len(initial_individuals or [])
        population = create_population(settings, all_pairs, population_size, initial_individuals)

    best_individuals = []

    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(start_generation, settings.generations):
            logger.info(f"Generation {gen+1}")
                        
            # Evaluate fitness in parallel
            try:
                fitnesses = pool.starmap(run_backtest, 
                    [(ind.genes, ind.trading_pairs, gen+1) for ind in population.individuals])
                
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
                mutate(ind, settings.mutation_prob)  # 使用设定的突变概率
                ind.after_genetic_operation(settings.parameters)

            # Replace the population
            population.individuals = offspring

            # Find the best individual in the current generation
            best_individual = max(valid_individuals, key=lambda ind: ind.fitness)
            best_individuals.append((gen+1, best_individual))

            logger.info(f"Best individual in generation {gen+1}: Fitness: {best_individual.fitness}")

            # Save checkpoint every N generations
            if (gen + 1) % settings.checkpoint_frequency == 0:
                save_checkpoint(population, gen + 1, settings)

            gc.collect()  # Clean up memory at the end of each generation

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
    parser.add_argument('--resume', action='store_true', help='Resume from the latest checkpoint')
    args = parser.parse_args()

    try:
        # Initialize settings
        settings = Settings(args.config)

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
            save_best_individual(ind, gen, settings)

        # Log overall best individual
        overall_best = max(best_individuals, key=lambda x: x[1].fitness)
        logger.info(f"Overall best individual: Generation {overall_best[0]}, Fitness: {overall_best[1].fitness}")
        logger.info(f"Best trading pairs: {overall_best[1].trading_pairs}")
    
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
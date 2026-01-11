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
from optimization.genetic_optimizer import GeneticOptimizer
from optimization.optuna_optimizer import OptunaOptimizer
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
    """
    Legacy genetic algorithm function - now wraps GeneticOptimizer.

    Args:
        settings: Settings object
        initial_individuals: Optional list of initial individuals

    Returns:
        List of (generation, best_individual) tuples
    """
    all_pairs = load_trading_pairs(settings.config_file)
    optimizer = GeneticOptimizer(settings, settings.parameters, all_pairs)
    return optimizer.optimize(initial_individuals)


def run_optimization(settings: Settings, optimizer_type: str = 'genetic',
                     initial_individuals: List[Individual] = None) -> List[tuple[int, Individual]]:
    """
    Run optimization using the specified optimizer.

    Args:
        settings: Settings object containing optimization configuration
        optimizer_type: Type of optimizer to use ('genetic' or 'optuna')
        initial_individuals: Optional list of initial individuals

    Returns:
        List of (generation/trial, best_individual) tuples
    """
    all_pairs = load_trading_pairs(settings.config_file)

    if optimizer_type == 'optuna':
        logger.info("Using Optuna optimizer")
        optimizer = OptunaOptimizer(settings, settings.parameters, all_pairs)
    else:
        logger.info("Using Genetic Algorithm optimizer")
        optimizer = GeneticOptimizer(settings, settings.parameters, all_pairs)

    return optimizer.optimize(initial_individuals)


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
    parser = argparse.ArgumentParser(description='Run optimization for trading strategy')
    parser.add_argument('--config', type=str, default='ga.json', help='Path to the configuration file')
    parser.add_argument('--download', action='store_true', help='Download data before running the algorithm')
    parser.add_argument('--start-date', type=str, default='20240101', help='Start date for data download (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, default=date.today().strftime('%Y%m%d'), help='End date for data download (YYYYMMDD)')
    parser.add_argument('--resume', action='store_true', help='Resume from the latest checkpoint')
    parser.add_argument('--optimizer', type=str, default='genetic', choices=['genetic', 'optuna'],
                        help='Optimizer to use: genetic (default) or optuna')
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

        # Determine optimizer type (command line takes precedence over config)
        optimizer_type = args.optimizer
        if hasattr(settings, 'optimizer_type') and args.optimizer == 'genetic':
            optimizer_type = settings.optimizer_type

        # Run optimization
        logger.info(f"Starting optimization with {optimizer_type} optimizer")
        best_individuals = run_optimization(settings, optimizer_type)

        # Save best individuals
        for gen, ind in best_individuals:
            save_best_individual(ind, gen, settings)

        # Log overall best individual
        if best_individuals:
            overall_best = max(best_individuals, key=lambda x: x[1].fitness if x[1].fitness is not None else float('-inf'))
            logger.info(f"Overall best individual: Generation {overall_best[0]}, Fitness: {overall_best[1].fitness}")
            logger.info(f"Best trading pairs: {overall_best[1].trading_pairs}")
        else:
            logger.warning("No valid individuals found during optimization")

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
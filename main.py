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
from functools import lru_cache
from functools import wraps
import numpy as np


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

def calculate_population_diversity(population):
    # 如果没有个体，返回0
    if not population.individuals:
        return 0
    
    # 将所有个体的基因转换为numpy数组
    genes_array = np.array([ind.genes for ind in population.individuals])
    
    # 计算每个参数的最大值和最小值
    genes_min = np.min(genes_array, axis=0)
    genes_max = np.max(genes_array, axis=0)
    
    # 避免除以零（当最大值等于最小值时）
    denominator = genes_max - genes_min
    denominator[denominator == 0] = 1  # 对于相同的参数值，设置分母为1
    
    # 归一化基因
    normalized_genes = (genes_array - genes_min) / denominator
    
    # 计算归一化后的基因距离
    gene_distances = []
    for i in range(len(population.individuals)):
        for j in range(i + 1, len(population.individuals)):
            distance = np.mean(np.abs(normalized_genes[i] - normalized_genes[j]))
            gene_distances.append(distance)
    
    return np.mean(gene_distances) if gene_distances else 0

def genetic_algorithm(settings: Settings, initial_individuals: List[Individual] = None) -> List[tuple[int, Individual]]:
    # Load trading pairs
    all_pairs = load_trading_pairs(settings.config_file)
    
    # Load the latest checkpoint if it exists
    population, start_generation = load_latest_checkpoint(settings)
    if population is None:
        # Create initial population if no checkpoint was found
        population_size = settings.population_size - len(initial_individuals or [])
        if not settings.fix_pairs:
            population = Population.create_random(
                size=population_size,
                parameters=settings.parameters,
                trading_pairs=all_pairs,
                num_pairs=settings.num_pairs
            )
        else:
            population = Population.create_random(
                size=population_size,
                parameters=settings.parameters,
                trading_pairs=all_pairs,
                num_pairs=None
            )
        if initial_individuals:
            population.individuals.extend(initial_individuals)

    best_individuals = []

    with multiprocessing.Pool(processes=settings.pool_processes) as pool:
        for gen in range(start_generation, settings.generations):
            logger.info(f"Generation {gen+1}")
                        
            # Evaluate fitness in parallel
            try:
                fitnesses = pool.starmap(run_backtest, 
                    [(ind.genes, ind.trading_pairs, gen+1) for ind in population.individuals])
                
                for ind, fit in zip(population.individuals, fitnesses):
                    if fit is not None:
                        ind.fitness = fit
                    else:
                        logger.warning(f"Invalid fitness value for individual in generation {gen+1}")
                        ind.fitness = float('-inf')  # or some other appropriate default value
            except Exception as e:
                logger.error(f"Error during fitness calculation in generation {gen+1}: {str(e)}")
                # Handle the error appropriately, maybe by skipping this generation or terminating the algorithm
            
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

            # Calculate population diversity and adjust mutation probability
            diversity = calculate_population_diversity(population)
            logger.info("="*50)
            logger.info(f"🔍 POPULATION DIVERSITY: {diversity:.6f}")
            logger.info("="*50)
            
            if diversity < settings.diversity_threshold:
                current_mutation_prob = min(settings.mutation_prob * 2, 0.4)
                logger.info(f"Low population diversity detected ({diversity:.4f}). Increasing mutation probability to {current_mutation_prob:.4f}")
            else:
                current_mutation_prob = settings.mutation_prob
                logger.info(f"Population diversity: {diversity:.4f}, using base mutation probability: {current_mutation_prob:.4f}")

            # Use current_mutation_prob instead of settings.mutation_prob
            for ind in offspring:
                mutate(ind, current_mutation_prob)  # 使用动态调整的突变概率
                # Mutate trading pairs
                ind.mutate_trading_pairs(all_pairs, current_mutation_prob)  # 这里也使用动态调整的突变概率
                ind.after_genetic_operation(settings.parameters)

            # Replace the population
            population.individuals = offspring

            # Find the best individual in the current generation
            best_ind = max(valid_individuals, key=lambda ind: ind.fitness)
            best_individuals.append((gen+1, best_ind))

            logger.info(f"Best individual in generation {gen+1}: Fitness: {best_ind.fitness}")

            # Save checkpoint every N generations
            if (gen + 1) % settings.checkpoint_frequency == 0:
                save_checkpoint(population, gen + 1, settings)

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
        # Update parameters in settings
        settings.parameters = parameters

        # Create necessary directories
        create_directories([settings.results_dir, settings.best_generations_dir, settings.checkpoint_dir])

        # Download data if requested
        if args.download:
            start_date = datetime.strptime(args.start_date, '%Y%m%d').date()
            end_date = datetime.strptime(args.end_date, '%Y%m%d').date()
            logger.info(f"Downloading data from {start_date} to {end_date}")
            download_data(start_date, end_date)

        # Record start time
        start_time = time.time()

        # Run genetic algorithm
        all_pairs = load_trading_pairs(settings.config_file)
        initial_individuals = []

        if args.resume:
            logger.info("Resuming from the latest checkpoint")
            best_individuals = genetic_algorithm(settings)
        else:
            logger.info("Starting a new genetic algorithm run")
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

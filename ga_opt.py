import re
import os
import time
import json
import random
from deap import base, creator, tools, algorithms
import numpy as np
from template import strategy_params, render_strategy
import logging
import multiprocessing
from datetime import datetime, timedelta
import argparse

# Load configuration from JSON file
with open('ga.json', 'r') as config_file:
    config = json.load(config_file)

# Set proxy environment variables
for key, value in config['proxy'].items():
    os.environ[f'{key}_proxy'] = value

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check and create directories if they don't exist
for dir_name in [config['results_dir'], config['best_generations_dir']]:
    dir_path = os.path.join(config['project_dir'], dir_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory: {dir_path}")


def parse_backtest_results(output_file):
    with open(output_file, 'r') as f:
        content = f.read()

    # Check if the file contains the necessary information
    if "SUMMARY METRICS" not in content:
        print(f"Warning: {output_file} does not contain summary metrics. No trades were executed.")
        return {
            'total_profit_usdt': 0,
            'total_profit_percent': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'profit_factor': 0,
            'avg_profit': 0,
            'total_trades': 0,
            'daily_avg_trades': 0,
            'avg_trade_duration': 0
        }

    def extract_value(pattern, default=0, is_string=False):
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if is_string:
                return value
            try:
                return float(value)
            except ValueError:
                print(f"Could not convert to float: {value}")
                return default
        else:
            return default

    def parse_duration(duration_str):
        parts = duration_str.split(', ')
        total_minutes = 0
        for part in parts:
            if 'day' in part:
                total_minutes += int(part.split()[0]) * 24 * 60
            else:
                time_parts = part.split(':')
                total_minutes += int(time_parts[0]) * 60 + int(time_parts[1])
        return total_minutes

    parsed_result = {
        'total_profit_usdt': extract_value(r'Absolute profit\s*│\s*([-\d.]+)\s*USDT'),
        'total_profit_percent': extract_value(r'Total profit %\s*│\s*([\d.-]+)%') / 100,
        'win_rate': extract_value(r'│\s*TOTAL\s*│.*?│.*?│.*?│.*?│.*?│.*?(\d+(?:\.\d+)?)\s*│') / 100,
        'max_drawdown': extract_value(r'Max % of account underwater\s*│\s*([\d.]+)%') / 100,
        'sharpe_ratio': extract_value(r'Sharpe\s*│\s*([\d.]+)'),
        'sortino_ratio': extract_value(r'Sortino\s*│\s*([\d.]+)'),
        'profit_factor': extract_value(r'Profit factor\s*│\s*([\d.]+)'),
        'avg_profit': extract_value(r'Avg Profit %\s*([\d.-]+)'),
        'total_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*(\d+)\s*/'),
        'daily_avg_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*\d+\s*/\s*([\d.]+)'),
        'avg_trade_duration': parse_duration(extract_value(r'Avg\. Duration Winners\s*│\s*(.*?)\s*│', default='0:00:00', is_string=True))
    }

    return parsed_result

def fitness_function_buy(parsed_result):
    sortino = parsed_result['sortino_ratio']
    profit = parsed_result['total_profit_percent']
    trade_count = parsed_result['total_trades']
    avg_duration = parsed_result['avg_trade_duration']

    if trade_count < 10:
        return float('-inf')  # Heavily penalize low trade count

    # Adjust fitness based on average trade duration
    duration_factor = min(avg_duration / 1440, 1)  # Cap at 1 day (1440 minutes)
    fitness = sortino + (1 / trade_count) + duration_factor

    if profit <= 0:
        fitness = fitness / 2

    return fitness

def fitness_function_sell(parsed_result):
    sortino = parsed_result['sortino_ratio']
    profit = parsed_result['total_profit_percent']
    trade_count = parsed_result['total_trades']
    avg_profit = parsed_result['avg_profit']
    avg_duration = parsed_result['avg_trade_duration']

    if trade_count < 10:
        return float('-inf')  # Heavily penalize low trade count

    # Adjust fitness based on average trade duration
    duration_factor = min(avg_duration / 1440, 1)  # Cap at 1 day (1440 minutes)
    fitness = sortino + avg_profit * 0.1 + duration_factor

    if profit <= 0:
        fitness = fitness / 2

    return fitness

def evaluate_strategy(individual, generation):
    params = strategy_params.copy()
    params.update({
        'initial_entry_ratio': round(individual[0], 2),
        'new_sl_coef': round(individual[1], 2),
        'lookback_length': int(individual[2]),
        'upper_trigger_level': int(individual[3]),
        'lower_trigger_level': int(individual[4]),
        'buy_rsi': int(individual[5]),
        'sell_rsi': int(individual[6]),
        'atr_multiplier': round(individual[7], 1),
        'swing_window': int(individual[8]),
        'swing_min_periods': int(individual[9]),
        'swing_buffer': round(individual[10], 2),
        'buy_macd': round(individual[11], 2),
        'buy_ema_short': int(individual[12]),
        'buy_ema_long': int(individual[13]),
        'sell_macd': round(individual[14], 2),
        'sell_ema_short': int(individual[15]),
        'sell_ema_long': int(individual[16]),
        'volume_dca_int': int(individual[17]),
        'a_vol_coef': round(individual[18], 1),
        'dca_candles_modulo': int(individual[19]),
        'dca_threshold': round(individual[20], 2),
        'dca_multiplier': round(individual[21], 1),
        'max_dca_orders': int(individual[22]),
        'dca_profit_threshold': round(individual[23], 2),
    })
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    random_number = random.randint(1000, 9999)  # Generate a random 4-digit number
    strategy_name = f"DailyBuy_gen{generation}_{timestamp}_{random_number}"
    strategy_file = f"{config['strategy_dir']}/{strategy_name}.py"
    params['strategy_name'] = strategy_name
    
    # Render new strategy file
    rendered_strategy = render_strategy(params)
    
    # Save the rendered strategy to a file
    with open(strategy_file, 'w') as f:
        f.write(rendered_strategy)
    
    # Calculate the start_date for the timerange
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=18)
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    output_file = f"{config['results_dir']}/backtest_results_gen{generation}_{timestamp}_{random_number}.txt"
    
    for attempt in range(config['max_retries']):
        command = f"{config['freqtrade_path']} backtesting --strategy {strategy_name} --config {config['config_file']} --timerange {timerange} > {output_file}"
        out = os.system(command)
        
        if out == 0:
            logger.info(f"Backtesting successful for generation {generation}, individual {individual}")
            break
        else:
            if attempt < config['max_retries'] - 1:
                logger.warning(f"Backtesting failed for generation {generation}, individual {individual}. Retrying in {config['retry_delay']} seconds...")
                time.sleep(config['retry_delay'])
            else:
                logger.error(f"Backtesting failed after {config['max_retries']} attempts for generation {generation}, individual {individual}.")
                return (float('-inf'),)  # Heavily penalize failed backtests
    
    parsed_result = parse_backtest_results(output_file)
    
    if parsed_result['total_trades'] == 0:
        return (float('-inf'),)  # Heavily penalize strategies that don't trade
    
    fitness_buy = fitness_function_buy(parsed_result)
    fitness_sell = fitness_function_sell(parsed_result)
    
    # Combine buy and sell fitness scores
    combined_fitness = (fitness_buy + fitness_sell) / 2
    
    return (combined_fitness,)

def genetic_algorithm():
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # Now we're maximizing
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()
    
    # Define gene (parameter) ranges
    toolbox.register("initial_entry_ratio", random.uniform, 0.4, 1.0)
    toolbox.register("new_sl_coef", random.uniform, 0.3, 0.9)
    toolbox.register("lookback_length", random.randint, 1, 30)
    toolbox.register("upper_trigger_level", random.randint, 1, 300)
    toolbox.register("lower_trigger_level", random.randint, -300, -1)
    toolbox.register("buy_rsi", random.randint, 25, 60)
    toolbox.register("sell_rsi", random.randint, 50, 70)
    toolbox.register("atr_multiplier", random.uniform, 1.0, 3.0)
    toolbox.register("swing_window", random.randint, 10, 50)
    toolbox.register("swing_min_periods", random.randint, 1, 10)
    toolbox.register("swing_buffer", random.uniform, 0.01, 0.1)
    toolbox.register("buy_macd", random.uniform, -0.02, 0.02)
    toolbox.register("buy_ema_short", random.randint, 5, 50)
    toolbox.register("buy_ema_long", random.randint, 50, 200)
    toolbox.register("sell_macd", random.uniform, -0.02, 0.02)
    toolbox.register("sell_ema_short", random.randint, 5, 50)
    toolbox.register("sell_ema_long", random.randint, 50, 200)
    toolbox.register("volume_dca_int", random.randint, 1, 30)
    toolbox.register("a_vol_coef", random.uniform, 1.0, 2.0)
    toolbox.register("dca_candles_modulo", random.randint, 1, 100)
    toolbox.register("dca_threshold", random.uniform, 0.01, 0.5)
    toolbox.register("dca_multiplier", random.uniform, 1.0, 2.0)
    toolbox.register("max_dca_orders", random.randint, 1, 5)
    toolbox.register("dca_profit_threshold", random.uniform, -0.20, -0.05)

    # Create individuals and population
    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.initial_entry_ratio, toolbox.new_sl_coef, toolbox.lookback_length,
                      toolbox.upper_trigger_level, toolbox.lower_trigger_level, toolbox.buy_rsi,
                      toolbox.sell_rsi, toolbox.atr_multiplier, toolbox.swing_window,
                      toolbox.swing_min_periods, toolbox.swing_buffer, toolbox.buy_macd,
                      toolbox.buy_ema_short, toolbox.buy_ema_long, toolbox.sell_macd,
                      toolbox.sell_ema_short, toolbox.sell_ema_long, toolbox.volume_dca_int,
                      toolbox.a_vol_coef, toolbox.dca_candles_modulo, toolbox.dca_threshold,
                      toolbox.dca_multiplier, toolbox.max_dca_orders, toolbox.dca_profit_threshold), n=1)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register evaluation function
    toolbox.register("evaluate", evaluate_strategy)

    # Register genetic operators
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=config['tournament_size'])

    population = toolbox.population(n=config['population_size'])
    
    NGEN = config['generations']
    CXPB = config['crossover_prob']
    MUTPB = config['mutation_prob']

    # Record the best individual in each generation
    best_individuals = []

    # Create a pool of worker processes
    pool = multiprocessing.Pool(processes=config['pool_processes'])

    for gen in range(NGEN):
        logger.info(f"Generation {gen+1}")
        
        # Evaluate fitness in parallel using multiple processes
        fitnesses = pool.starmap(toolbox.evaluate, [(ind, gen+1) for ind in population])
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # Select individuals for the next generation
        offspring = toolbox.select(population, len(population))
        offspring = list(map(toolbox.clone, offspring))

        # Apply crossover and mutation
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < CXPB:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        for mutant in offspring:
            if random.random() < MUTPB:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate the fitness of new individuals
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = [toolbox.evaluate(ind, gen+1) for ind in invalid_ind]
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Replace the population
        population[:] = offspring

        # Find the best individual in the current generation
        best_ind = tools.selBest(population, 1)[0]
        best_individuals.append((gen+1, best_ind))

        logger.info(f"Best individual in generation {gen+1}: {best_ind}, Fitness: {best_ind.fitness.values[0]}")

    # Close the pool of worker processes
    pool.close()
    pool.join()

    return best_individuals

def download_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=18)
    timerange = f"{start_date.strftime('%Y%m%d')}-"
    
    download_command = f"{config['freqtrade_path']} download-data --config {config['config_file']} --timerange {timerange} -t 5m 15m 1h 4h 1d 1w 1M"
    
    logger.info("Downloading data...")
    out = os.system(download_command)
    
    if out == 0:
        logger.info("Data download completed successfully.")
    else:
        logger.error("Data download failed.")
        raise Exception("Failed to download data")

def optimize_and_update(download_data_flag):
    os.chdir(config['project_dir'])
    
    # Download data before running the genetic algorithm if flag is set
    if download_data_flag:
        download_data()
    
    # Remove the timerange update in config as it's no longer needed
    # The timerange is now calculated dynamically in evaluate_strategy function
    
    best_individuals = genetic_algorithm()
    
    for gen, best_params in best_individuals:
        if best_params.fitness.values[0] > 0:
            params = strategy_params.copy()
            params.update({
                'initial_entry_ratio': round(best_params[0], 2),
                'new_sl_coef': round(best_params[1], 2),
                'lookback_length': int(best_params[2]),
                'upper_trigger_level': int(best_params[3]),
                'lower_trigger_level': int(best_params[4]),
                'buy_rsi': int(best_params[5]),
                'sell_rsi': int(best_params[6]),
                'atr_multiplier': round(best_params[7], 1),
                'swing_window': int(best_params[8]),
                'swing_min_periods': int(best_params[9]),
                'swing_buffer': round(best_params[10], 2),
                'buy_macd': round(best_params[11], 2),
                'buy_ema_short': int(best_params[12]),
                'buy_ema_long': int(best_params[13]),
                'sell_macd': round(best_params[14], 2),
                'sell_ema_short': int(best_params[15]),
                'sell_ema_long': int(best_params[16]),
                'volume_dca_int': int(best_params[17]),
                'a_vol_coef': round(best_params[18], 1),
                'dca_candles_modulo': int(best_params[19]),
                'dca_threshold': round(best_params[20], 2),
                'dca_multiplier': round(best_params[21], 1),
                'max_dca_orders': int(best_params[22]),
                'dca_profit_threshold': round(best_params[23], 2),
            })
            
            strategy_name = f"DailyBuy_{gen}"
            params['strategy_name'] = strategy_name
            
            strategy_file = f"{config['best_generations_dir']}/{strategy_name}.py"
            
            # Use render_strategy function to generate strategy file
            rendered_strategy = render_strategy(params)
            
            # Save the rendered strategy to a file
            with open(strategy_file, 'w') as f:
                f.write(rendered_strategy)
            
            logger.info(f"Generated strategy for generation {gen} with fitness: {best_params.fitness.values[0]}")
        else:
            logger.info(f"Generation {gen} did not result in any trades.")

if __name__ == "__main__":
    multiprocessing.freeze_support()  # This line helps with Windows compatibility
    
    parser = argparse.ArgumentParser(description='Run genetic algorithm optimization')
    parser.add_argument('--download-data', action='store_true', help='Download data before optimization')
    args = parser.parse_args()
    
    optimize_and_update(args.download_data)

import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function
from strategy.template import strategy_template, strategy_params

def render_strategy(params: List[float], strategy_name: str) -> str:
    print(f"Input params: {params}")
    print(f"Input strategy_name: {strategy_name}")

    param_keys = [
        'initial_entry_ratio', 'new_sl_coef', 'lookback_length', 'upper_trigger_level',
        'lower_trigger_level', 'buy_rsi', 'sell_rsi', 'atr_multiplier', 'swing_window',
        'swing_min_periods', 'swing_buffer', 'buy_macd', 'buy_ema_short', 'buy_ema_long',
        'sell_macd', 'sell_ema_short', 'sell_ema_long', 'volume_dca_int', 'a_vol_coef',
        'dca_candles_modulo', 'dca_threshold', 'dca_multiplier', 'max_dca_orders',
        'dca_profit_threshold'
    ]
    
    if len(params) != len(param_keys):
        raise ValueError(f"Expected {len(param_keys)} parameters, but got {len(params)}")
    
    params_dict = {}
    for key, value in zip(param_keys, params):
        if key == 'initial_entry_ratio':
            params_dict[key] = min(round(float(value), 2), 0.99)
        elif key in ['new_sl_coef', 'atr_multiplier', 'swing_buffer', 
                   'buy_macd', 'sell_macd', 'a_vol_coef', 'dca_threshold', 'dca_multiplier', 
                   'dca_profit_threshold']:
            params_dict[key] = round(float(value), 2)
        elif key in ['lookback_length', 'upper_trigger_level', 'lower_trigger_level', 'buy_rsi', 
                     'sell_rsi', 'swing_window', 'swing_min_periods', 'buy_ema_short', 'buy_ema_long', 
                     'sell_ema_short', 'sell_ema_long', 'volume_dca_int', 'dca_candles_modulo', 
                     'max_dca_orders']:
            params_dict[key] = int(value)
        else:
            params_dict[key] = value
    
    print(f"Converted params_dict: {params_dict}")
    
    strategy_params_copy = strategy_params.copy()
    strategy_params_copy.update(params_dict)
    strategy_params_copy['strategy_name'] = strategy_name
    
    print(f"Final strategy_params: {strategy_params_copy}")
    
    rendered_strategy = strategy_template.substitute(strategy_params_copy)
    print(f"Rendered strategy (first 100 characters): {rendered_strategy[:100]}...")
    
    return rendered_strategy

def run_backtest(params: List[float], generation: int, start_date: datetime) -> Tuple[float, str]:
    timestamp = int(time.time())
    random_id = random.randint(1000, 9999)
    strategy_name = f"GeneTrader_gen{generation}_{timestamp}_{random_id}"
    strategy_file = f"{settings.strategy_dir}/{strategy_name}.py"
    
    rendered_strategy = render_strategy(params, strategy_name)
    with open(strategy_file, 'w') as f:
        f.write(rendered_strategy)
    
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    # Include time range in the output file name
    output_file = f"scripts/outputs/backtest_results_gen{generation}_{start_date.strftime('%Y%m%d')}_{timestamp}_{random_id}.txt"
    
    for attempt in range(settings.max_retries):
        command = (
            f"{settings.freqtrade_path} backtesting "
            f"--strategy {strategy_name} "
            f"-c {os.path.abspath(settings.config_file)} "
            f"--timerange {timerange} "
            f"-d {os.path.abspath(settings.data_dir)} "
            f"--userdir {os.path.abspath(settings.user_dir)} "
            f"> {output_file}"
        )
        logger.info(f"Running command: {command}")
        out = os.system(command)
        
        if out == 0:
            logger.info(f"Backtesting successful for generation {generation} and timerange {timerange}")
            break
        else:
            if attempt < settings.max_retries - 1:
                logger.warning(f"Backtesting failed for generation {generation} and timerange {timerange}. Retrying in {settings.retry_delay} seconds...")
                time.sleep(settings.retry_delay)
    
    parsed_result = parse_backtest_results(output_file)
    
    if parsed_result['total_trades'] == 0:
        return float('-inf'), output_file
    
    return fitness_function(parsed_result), output_file

def backtest_multiple_periods(genes: List[float], generation: int, start_dates: List[datetime]) -> Dict:
    results = {}
    for start_date in start_dates:
        fitness, output_file = run_backtest(genes, generation, start_date)
        timerange = f"{start_date.strftime('%Y%m%d')}-"
        results[timerange] = {
            'fitness': fitness,
            'output_file': output_file
        }
    return results

def backtest_best_generations():
    # Define your start dates here
    start_dates = [
        datetime(2024, 1, 1),
        datetime(2024, 4, 1),
        datetime(2024, 7, 1),
        datetime(2024, 8, 1),
    ]

    results = {}
    for filename in os.listdir('bestgenerations'):
        if filename.endswith('.json'):
            with open(os.path.join('bestgenerations', filename), 'r') as f:
                data = json.load(f)
                genes = data['genes']
                generation = data['generation']
            
            period_results = backtest_multiple_periods(genes, generation, start_dates)
            results[generation] = {
                'period_results': period_results,
                'genes': genes
            }
    
    # Print and compare results
    for generation, data in sorted(results.items()):
        print(f"Generation {generation}:")
        for timerange, period_data in data['period_results'].items():
            print(f"  Timerange {timerange}:")
            print(f"    Fitness: {period_data['fitness']}")
            print(f"    Output file: {period_data['output_file']}")
        print(f"  Genes: {data['genes']}")
        print()

    # Find the best strategy (based on average fitness across all periods)
    best_generation = max(results, key=lambda x: sum(period['fitness'] for period in results[x]['period_results'].values()) / len(results[x]['period_results']))
    print(f"Best strategy: Generation {best_generation}")
    for timerange, period_data in results[best_generation]['period_results'].items():
        print(f"  Timerange {timerange}:")
        print(f"    Fitness: {period_data['fitness']}")
        print(f"    Output file: {period_data['output_file']}")
    print(f"  Genes: {results[best_generation]['genes']}")

if __name__ == "__main__":
    # Ensure the outputs directory exists
    os.makedirs("scripts/outputs", exist_ok=True)
    backtest_best_generations()
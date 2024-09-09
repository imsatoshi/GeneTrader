import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import time
from datetime import datetime
from typing import List, Dict
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function

def run_backtest(strategy_name: str, start_date: datetime) -> Dict:
    timestamp = int(time.time())
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    output_file = f"scripts/outputs/backtest_results_{strategy_name}_{start_date.strftime('%Y%m%d')}_{timestamp}.txt"
    
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
            logger.info(f"Backtesting successful for {strategy_name} and timerange {timerange}")
            break
        else:
            if attempt < settings.max_retries - 1:
                logger.warning(f"Backtesting failed for {strategy_name} and timerange {timerange}. Retrying in {settings.retry_delay} seconds...")
                time.sleep(settings.retry_delay)
    
    parsed_result = parse_backtest_results(output_file)
    
    if parsed_result['total_trades'] == 0:
        fitness = float('-inf')
    else:
        fitness = fitness_function(parsed_result)
    
    return {
        'fitness': fitness,
        'output_file': output_file,
        'parsed_result': parsed_result
    }

def benchmark_strategy(strategy_name: str, start_dates: List[datetime]) -> Dict:
    results = {}
    for start_date in start_dates:
        result = run_backtest(strategy_name, start_date)
        timerange = f"{start_date.strftime('%Y%m%d')}-"
        results[timerange] = result
    return results

def print_benchmark_results(strategy_name: str, results: Dict):
    print(f"Benchmark results for {strategy_name}:")
    for timerange, data in results.items():
        print(f"  Timerange {timerange}:")
        print(f"    Fitness: {data['fitness']}")
        print(f"    Output file: {data['output_file']}")
        print(f"    Total trades: {data['parsed_result']['total_trades']}")
        print(f"    Total profit: {data['parsed_result']['total_profit']}")
        print(f"    Profit ratio: {data['parsed_result']['profit_ratio']}")
        print()

if __name__ == "__main__":
    # Ensure the outputs directory exists
    os.makedirs("scripts/outputs", exist_ok=True)

    strategy_name = "DailyBuyStrategy_old"
    # strategy_name = "GeneTrader_gen6_1725791922_1410"
    start_dates = [
        datetime(2024, 1, 1),
        datetime(2024, 4, 1),
        datetime(2024, 7, 1),
        datetime(2024, 8, 1),
    ]

    results = benchmark_strategy(strategy_name, start_dates)
    print_benchmark_results(strategy_name, results)

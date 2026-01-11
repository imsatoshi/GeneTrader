"""Benchmark utility for evaluating trading strategies across multiple time ranges."""
import sys
import os
import subprocess

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import time
from datetime import datetime
from typing import List, Dict, Any
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function


def run_backtest(strategy_name: str, start_date: datetime) -> Dict[str, Any]:
    """Run a backtest for a strategy starting from a specific date.

    Args:
        strategy_name: Name of the strategy to backtest
        start_date: Start date for the backtest

    Returns:
        Dictionary containing fitness score, output file path, and parsed results
    """
    timestamp = int(time.time())
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    output_file = f"scripts/outputs/backtest_results_{strategy_name}_{start_date.strftime('%Y%m%d')}_{timestamp}.txt"

    # Build command as a list for subprocess.run (safer than os.system)
    cmd_args = [
        settings.freqtrade_path,
        "backtesting",
        "--strategy", strategy_name,
        "-c", os.path.abspath(settings.config_file),
        "--timerange", timerange,
        "-d", os.path.abspath(settings.data_dir),
        "--userdir", os.path.abspath(settings.user_dir),
    ]

    for attempt in range(settings.max_retries):
        logger.info(f"Running command: {' '.join(cmd_args)}")
        try:
            with open(output_file, 'w') as outf:
                result = subprocess.run(
                    cmd_args,
                    stdout=outf,
                    stderr=subprocess.STDOUT,
                    timeout=600  # 10 minute timeout
                )

            if result.returncode == 0:
                logger.info(f"Backtesting successful for {strategy_name} and timerange {timerange}")
                break
            else:
                if attempt < settings.max_retries - 1:
                    logger.warning(f"Backtesting failed for {strategy_name} and timerange {timerange}. "
                                   f"Retrying in {settings.retry_delay} seconds...")
                    time.sleep(settings.retry_delay)
        except subprocess.TimeoutExpired:
            logger.error(f"Backtest timed out for {strategy_name}")
            if attempt < settings.max_retries - 1:
                time.sleep(settings.retry_delay)

    parsed_result = parse_backtest_results(output_file)

    if parsed_result['total_trades'] == 0:
        fitness = float('-inf')
    else:
        # fitness_function requires: parsed_result, generation, strategy_name, timeframe
        fitness = fitness_function(parsed_result, 0, strategy_name, "benchmark")

    return {
        'fitness': fitness,
        'output_file': output_file,
        'parsed_result': parsed_result
    }

def benchmark_strategy(strategy_name: str, start_dates: List[datetime]) -> Dict[str, Any]:
    """Run backtests for a strategy across multiple start dates.

    Args:
        strategy_name: Name of the strategy to benchmark
        start_dates: List of start dates to test

    Returns:
        Dictionary mapping timeranges to their benchmark results
    """
    results = {}
    for start_date in start_dates:
        result = run_backtest(strategy_name, start_date)
        timerange = f"{start_date.strftime('%Y%m%d')}-"
        results[timerange] = result
    return results


def print_benchmark_results(strategy_name: str, results: Dict[str, Any]) -> None:
    """Print formatted benchmark results.

    Args:
        strategy_name: Name of the strategy tested
        results: Dictionary of benchmark results by timerange
    """
    print(f"\nBenchmark results for {strategy_name}:")
    print("=" * 60)
    for timerange, data in results.items():
        parsed = data['parsed_result']
        print(f"\n  Timerange: {timerange}")
        print(f"    Fitness:           {data['fitness']:.4f}" if data['fitness'] != float('-inf') else "    Fitness:           -inf")
        print(f"    Output file:       {data['output_file']}")
        print(f"    Total trades:      {parsed['total_trades']}")
        print(f"    Total profit %:    {parsed['total_profit_percent'] * 100:.2f}%")
        print(f"    Total profit USDT: {parsed['total_profit_usdt']:.2f}")
        print(f"    Win rate:          {parsed['win_rate'] * 100:.2f}%")
        print(f"    Max drawdown:      {parsed['max_drawdown'] * 100:.2f}%")
        print(f"    Sharpe ratio:      {parsed['sharpe_ratio']:.2f}")

if __name__ == "__main__":
    # Ensure the outputs directory exists
    os.makedirs("scripts/outputs", exist_ok=True)

    strategy_name = "DailyBuyStrategy"
    start_dates = [
        datetime(2024, 1, 1),
        datetime(2024, 4, 1),
        datetime(2024, 7, 1),
        datetime(2024, 8, 1),
    ]

    results = benchmark_strategy(strategy_name, start_dates)
    print_benchmark_results(strategy_name, results)

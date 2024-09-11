import os
import sys
from typing import Dict, Tuple

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from strategy.evaluation import parse_backtest_results, fitness_function
from utils.logging_config import logger

def process_results_directory(directory: str) -> Tuple[str, float, Dict[str, float], str, float, Dict[str, float]]:
    # best_file = ""
    # best_fitness = float('-inf')
    best_results = {}
    max_profit_file = ""
    max_profit = float('-inf')
    max_profit_results = {}

    for filename in os.listdir(directory):
        if filename.startswith('backtest_results_') and filename.endswith('.txt'):
            file_path = os.path.join(directory, filename)
            try:
                results = parse_backtest_results(file_path)
                profit = results.get('total_profit_usdt', 0)
                if profit > max_profit:
                    max_profit = profit
                    max_profit_file = file_path
                    max_profit_results = results
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")

    return best_results, max_profit_file, max_profit, max_profit_results

def analyze_results():
    results_dir = os.path.join(project_root, 'results')
    best_results, max_profit_file, max_profit, max_profit_results = process_results_directory(results_dir)

    print("\nParsed results for the best strategy:")
    for key, value in best_results.items():
        print(f"{key}: {value}")

    print(f"\nFile with maximum profit: {max_profit_file}")
    print(f"Maximum profit: {max_profit}")

    print("\nParsed results for the strategy with maximum profit:")
    for key, value in max_profit_results.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    analyze_results()

import os
import sys
from typing import Dict, Tuple

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from strategy.evaluation import parse_backtest_results, fitness_function
from utils.logging_config import logger

def process_results_directory(directory: str) -> Tuple[str, float, Dict[str, float]]:
    best_file = ""
    best_fitness = float('-inf')
    best_results = {}

    for filename in os.listdir(directory):
        if filename.startswith('backtest_results_') and filename.endswith('.txt'):
            file_path = os.path.join(directory, filename)
            try:
                results = parse_backtest_results(file_path)
                fitness = fitness_function(results)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_file = file_path
                    best_results = results
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")

    return best_file, best_fitness, best_results

def analyze_results():
    results_dir = os.path.join(project_root, 'results')
    best_file, best_fitness, best_results = process_results_directory(results_dir)

    if best_file:
        print(f"File with highest fitness score: {best_file}")
        print(f"Fitness score: {best_fitness}")

        print("\nParsed results for the best strategy:")
        for key, value in best_results.items():
            print(f"{key}: {value}")
    else:
        print("No valid backtest result files found in the results directory.")

if __name__ == "__main__":
    analyze_results()

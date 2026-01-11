"""Helper functions for fitness extraction and logging analysis.

This module consolidates duplicated fitness extraction functions
that were previously in get_max_fitness.py and scripts/workflow.py.
"""
import re
from typing import Optional


def extract_fitness(line: str) -> Optional[float]:
    """Extract fitness value from a log line.

    Args:
        line: Log line that may contain fitness information

    Returns:
        Fitness value as float, or None if not found
    """
    match = re.search(r'Fitness:\s*([-\d.]+)', line)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_generation(line: str) -> Optional[int]:
    """Extract generation number from a log line.

    Args:
        line: Log line that may contain generation information

    Returns:
        Generation number as int, or None if not found
    """
    match = re.search(r'Generation\s*(\d+)', line)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def extract_strategy_name(line: str) -> Optional[str]:
    """Extract strategy name from a log line.

    Args:
        line: Log line that may contain strategy name

    Returns:
        Strategy name as string, or None if not found
    """
    match = re.search(r'Strategy:\s*(\S+)', line)
    if match:
        return match.group(1)
    return None


def parse_fitness_log(log_file: str) -> dict:
    """Parse fitness log file and extract generation statistics.

    Args:
        log_file: Path to the fitness log file

    Returns:
        Dictionary with generation data including max fitness and best strategy
    """
    generations = {}
    current_gen = None

    try:
        with open(log_file, 'r') as file:
            for line in file:
                gen = extract_generation(line)
                if gen is not None:
                    current_gen = gen
                    if current_gen not in generations:
                        generations[current_gen] = {
                            'max_fitness': None,
                            'max_fitness_line': '',
                            'strategy_name': ''
                        }

                fitness = extract_fitness(line)
                if fitness is not None and current_gen is not None:
                    gen_data = generations[current_gen]
                    if gen_data['max_fitness'] is None or fitness > gen_data['max_fitness']:
                        gen_data['max_fitness'] = fitness
                        gen_data['max_fitness_line'] = line.strip()
                        strategy_name = extract_strategy_name(line)
                        if strategy_name:
                            gen_data['strategy_name'] = strategy_name

    except FileNotFoundError:
        return {}

    return generations


def get_best_strategy(generations: dict) -> tuple:
    """Find the best strategy across all generations.

    Args:
        generations: Dictionary from parse_fitness_log

    Returns:
        Tuple of (max_fitness, best_strategy_name, best_generation)
    """
    max_fitness = float('-inf')
    best_strategy = None
    best_gen = None

    for gen, data in generations.items():
        if data['max_fitness'] is not None and data['max_fitness'] > max_fitness:
            max_fitness = data['max_fitness']
            best_strategy = data['strategy_name']
            best_gen = gen

    return max_fitness, best_strategy, best_gen

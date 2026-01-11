#!/usr/bin/env python3
"""Script to analyze fitness log and find best performing strategies.

This module uses the centralized fitness_helpers module for all
log parsing operations to avoid code duplication.
"""
import glob
from typing import Optional

from utils.fitness_helpers import (
    extract_final_fitness as extract_fitness,
    extract_generation,
    extract_strategy_name,
    extract_win_rate
)


def get_config_file(strategy_name: str) -> Optional[str]:
    """Find config file matching strategy name."""
    last_four_digits = strategy_name[-4:]
    config_files = glob.glob(f"user_data/temp_*_{last_four_digits}.json")
    return config_files[0] if config_files else None


def main():
    """Main function to analyze fitness log."""
    generations = {}
    current_gen = None

    try:
        with open('logs/fitness_log.txt', 'r') as file:
            for line in file:
                gen = extract_generation(line)
                if gen is not None:
                    current_gen = gen
                    if current_gen not in generations:
                        generations[current_gen] = {
                            'max_fitness': None,
                            'max_fitness_line': '',
                            'strategy_name': '',
                            'win_rate': None
                        }

                fitness = extract_fitness(line)
                win_rate = extract_win_rate(line)
                if fitness is not None and current_gen is not None:
                    gen_data = generations[current_gen]
                    if gen_data['max_fitness'] is None or fitness > gen_data['max_fitness']:
                        gen_data['max_fitness'] = fitness
                        gen_data['max_fitness_line'] = line.strip()
                        gen_data['strategy_name'] = extract_strategy_name(line) or ''
                        gen_data['win_rate'] = win_rate
    except FileNotFoundError:
        print("Error: logs/fitness_log.txt not found")
        return

    if not generations:
        print("No valid generations or fitness values found in the file.")
        return

    overall_max_fitness = float('-inf')
    overall_best_gen = None

    for gen, data in sorted(generations.items()):
        if data['max_fitness'] is not None:
            print(f"Generation {gen} max fitness:")
            print(data['max_fitness_line'])
            print(f"Maximum fitness: {data['max_fitness']}")
            print(f"Win Rate: {data['win_rate']}")

            strategy_name = data['strategy_name'].rstrip(',')
            config_file = get_config_file(strategy_name)
            if not config_file:
                print(f"Warning: No matching config file found for strategy {strategy_name}")
            print()

            if data['max_fitness'] > overall_max_fitness:
                overall_max_fitness = data['max_fitness']
                overall_best_gen = gen
        else:
            print(f"Generation {gen}: No valid fitness values found\n")

    if overall_best_gen is not None:
        print("Overall best fitness:")
        print(generations[overall_best_gen]['max_fitness_line'])
        print(f"Maximum fitness: {overall_max_fitness}")

        best_strategy_name = generations[overall_best_gen]['strategy_name'].rstrip(',')
        best_config_file = get_config_file(best_strategy_name)

        print(f"Config file: {best_config_file}")
        print(f"Strategy: {best_strategy_name}")

    print("\nDebug information:")
    print(f"Total generations processed: {len(generations)}")
    has_fitness = any(gen['max_fitness'] is not None for gen in generations.values())
    print(f"Found any fitness values: {'Yes' if has_fitness else 'No'}")


if __name__ == "__main__":
    main()

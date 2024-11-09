import re
import os
import glob

def extract_fitness(line):
    match = re.search(r'Final Fitness: ([-\d.]+)$', line)
    return float(match.group(1)) if match else None

def extract_generation(line):
    match = re.search(r'Generation: (\d+)', line)
    return int(match.group(1)) if match else None

def extract_strategy_name(line):
    match = re.search(r'Strategy: (\S+)', line)
    return match.group(1) if match else None

def get_config_file(strategy_name):
    last_four_digits = strategy_name[-4:]
    config_files = glob.glob(f"user_data/temp_*_{last_four_digits}.json")
    return config_files[0] if config_files else None

generations = {}
current_gen = None

with open('logs/fitness_log.txt', 'r') as file:
    for line in file:
        gen = extract_generation(line)
        if gen is not None:
            current_gen = gen
            if current_gen not in generations:
                generations[current_gen] = {'max_fitness': None, 'max_fitness_line': '', 'strategy_name': ''}
        
        fitness = extract_fitness(line)
        if fitness is not None and current_gen is not None:
            if generations[current_gen]['max_fitness'] is None or fitness > generations[current_gen]['max_fitness']:
                generations[current_gen]['max_fitness'] = fitness
                generations[current_gen]['max_fitness_line'] = line.strip()
                generations[current_gen]['strategy_name'] = extract_strategy_name(line)

# 创建一个文件来存储所有的回测命令
with open('backtesting_commands.sh', 'w') as command_file:
    command_file.write("#!/bin/bash\n\n")  # 添加shebang行

    if generations:
        overall_max_fitness = float('-inf')
        overall_best_gen = None

        for gen, data in sorted(generations.items()):
            if data['max_fitness'] is not None:
                print(f"Generation {gen} max fitness:")
                print(data['max_fitness_line'])
                print(f"Maximum fitness: {data['max_fitness']}")
                
                strategy_name = data['strategy_name'][:-1]
                config_file = get_config_file(strategy_name)
                if config_file:
                    backtesting_command = f"/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade backtesting --strategy {strategy_name} -c {config_file} --timerange 20240101- --timeframe-detail 1m > generation_{gen}.txt"
                    print(f"Backtesting command:")
                    print(backtesting_command)
                    command_file.write(backtesting_command + "\n\n")
                else:
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
            
            best_strategy_name = generations[overall_best_gen]['strategy_name']
            best_config_file = get_config_file(best_strategy_name)
            if best_config_file:
                best_backtesting_command = f"/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade backtesting --strategy {best_strategy_name} -c {best_config_file} --timerange 20240401- --timeframe-detail 1m > best_generation_{overall_best_gen}.txt"
                print("Best strategy backtesting command:")
                print(best_backtesting_command)
                command_file.write("# Best strategy backtesting command\n")
                command_file.write(best_backtesting_command + "\n")
            else:
                print(f"Warning: No matching config file found for best strategy {best_strategy_name}")
    else:
        print("No valid generations or fitness values found in the file.")

print("\nDebug information:")
print(f"Total generations processed: {len(generations)}")
print(f"Found any fitness values: {'Yes' if any(gen['max_fitness'] is not None for gen in generations.values()) else 'No'}")
print(f"\nAll backtesting commands have been written to 'backtesting_commands.sh'")

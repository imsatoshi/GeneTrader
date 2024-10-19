import re

def extract_fitness(line):
    # 更新正则表达式以匹配新的格式
    match = re.search(r'Final Fitness: ([\d.]+)', line)
    return float(match.group(1)) if match else 0

max_fitness = 0
max_fitness_line = ''

with open('fitness_log.txt', 'r') as file:
    for line in file:
        fitness = extract_fitness(line)
        if fitness > max_fitness:
            max_fitness = fitness
            max_fitness_line = line.strip()

if max_fitness_line:
    print("Line with maximum fitness:")
    print(max_fitness_line)
    print(f"Maximum fitness: {max_fitness}")
else:
    print("No valid fitness values found in the file.")

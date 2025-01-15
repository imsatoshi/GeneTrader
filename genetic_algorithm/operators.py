import random
from typing import List, Tuple  # Add Tuple to the imports
from genetic_algorithm.individual import Individual

def crossover(parent1: Individual, parent2: Individual, with_pair=True) -> Tuple[Individual, Individual]:
    # Crossover genes
    point = random.randint(1, len(parent1.genes) - 1)
    child1_genes = parent1.genes[:point] + parent2.genes[point:]
    child2_genes = parent2.genes[:point] + parent1.genes[point:]
    
    # Crossover trading pairs
    if not with_pair:
        child1_pairs_index, child2_pairs_index = parent1.crossover_trading_pairs(parent2)

        return Individual(child1_genes, child1_pairs_index, parent1.param_types), Individual(child2_genes, child2_pairs_index, parent2.param_types)
    else:
        return Individual(child1_genes, parent1.trading_pairs_index, parent1.param_types), Individual(child2_genes, parent2.trading_pairs_index, parent2.param_types)

def mutate(individual: Individual, mutation_rate: float, all_pairs=None):
    for i in range(len(individual.genes)):
        if random.random() < mutation_rate:
            param_type = individual.param_types[i]
            
            if isinstance(param_type, dict) and 'type' in param_type:
                mutation_strategy = random.choice(['noise', 'reset', 'scale'])
                
                if mutation_strategy == 'noise':
                    # 添加高斯噪声
                    noise = random.gauss(0, 0.1)
                    if param_type['type'] == 'Int':
                        new_value = int(individual.genes[i] + round(noise))
                        individual.genes[i] = max(param_type['start'], min(param_type['end'], new_value))
                    elif param_type['type'] == 'Decimal':
                        new_value = individual.genes[i] + noise
                        individual.genes[i] = max(param_type['start'], min(param_type['end'], new_value))
                        individual.genes[i] = round(individual.genes[i], param_type['decimal_places'])
                
                elif mutation_strategy == 'reset':
                    # 在允许范围内重置
                    if param_type['type'] == 'Int':
                        individual.genes[i] = random.randint(int(param_type['start']), int(param_type['end']))
                    elif param_type['type'] == 'Decimal':
                        individual.genes[i] = random.uniform(param_type['start'], param_type['end'])
                        individual.genes[i] = round(individual.genes[i], param_type['decimal_places'])
                
                else:  # scale
                    # 按比例缩放并确保在范围内
                    scale_factor = random.uniform(0.8, 1.2)
                    if param_type['type'] == 'Int':
                        new_value = int(individual.genes[i] * scale_factor)
                        individual.genes[i] = max(param_type['start'], min(param_type['end'], new_value))
                    elif param_type['type'] == 'Decimal':
                        new_value = individual.genes[i] * scale_factor
                        individual.genes[i] = max(param_type['start'], min(param_type['end'], new_value))
                        individual.genes[i] = round(individual.genes[i], param_type['decimal_places'])
            
            elif isinstance(individual.genes[i], bool):
                # 布尔类型：随机翻转
                individual.genes[i] = not individual.genes[i]
            
            elif isinstance(individual.genes[i], list):
                # 列表类型：随机修改列表中的一个元素
                individual.genes[i] = random.choice(param_type['options'])
        individual.mutate_trading_pairs(all_pairs, mutation_rate)

        individual.after_genetic_operation(individual.param_types)

def select_tournament(population: List[Individual], tournament_size: int) -> Individual:
    tournament = random.sample(population, tournament_size)
    return max(tournament, key=lambda ind: ind.fitness)

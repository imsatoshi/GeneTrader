import random
from typing import List, Tuple  # Add Tuple to the imports
from genetic_algorithm.individual import Individual

def crossover(parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
    # Crossover genes
    point = random.randint(1, len(parent1.genes) - 1)
    child1_genes = parent1.genes[:point] + parent2.genes[point:]
    child2_genes = parent2.genes[:point] + parent1.genes[point:]
    
    # Crossover trading pairs
    all_pairs = list(set(parent1.trading_pairs + parent2.trading_pairs))
    random.shuffle(all_pairs)
    
    child1_pairs = all_pairs[:len(parent1.trading_pairs)]
    child2_pairs = all_pairs[:len(parent2.trading_pairs)]

    return Individual(child1_genes, child1_pairs), Individual(child2_genes, child2_pairs)

def mutate(individual: Individual, mutation_rate: float):
    for i in range(len(individual.genes)):
        if random.random() < mutation_rate:
            individual.genes[i] += random.gauss(0, 0.1)

def select_tournament(population: List[Individual], tournament_size: int) -> Individual:
    tournament = random.sample(population, tournament_size)
    return max(tournament, key=lambda ind: ind.fitness)

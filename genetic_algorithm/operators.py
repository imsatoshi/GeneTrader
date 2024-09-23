import random
from typing import List, Tuple  # Add Tuple to the imports
from genetic_algorithm.individual import Individual

def crossover(parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:  # Use Tuple from typing
    point = random.randint(1, len(parent1.genes) - 1)
    child1_genes = parent1.genes[:point] + parent2.genes[point:]
    child2_genes = parent2.genes[:point] + parent1.genes[point:]
    return Individual(child1_genes), Individual(child2_genes)

def mutate(individual: Individual, mutation_rate: float):
    for i in range(len(individual.genes)):
        if random.random() < mutation_rate:
            individual.genes[i] += random.gauss(0, 0.1)

def select_tournament(population: List[Individual], tournament_size: int) -> Individual:
    tournament = random.sample(population, tournament_size)
    return max(tournament, key=lambda ind: ind.fitness)
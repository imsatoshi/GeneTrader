from typing import List
from genetic_algorithm.individual import Individual

class Population:
    def __init__(self, individuals: List[Individual]):
        self.individuals = individuals

    @classmethod
    def create_random(cls, size: int):
        return cls([Individual.create_random() for _ in range(size)])

    def get_best(self) -> Individual:
        return max(self.individuals, key=lambda ind: ind.fitness)
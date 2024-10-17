from typing import List
import random
import copy

class Individual:
    def __init__(self, genes: List[float], trading_pairs: List[str]):
        self.genes = genes
        self.trading_pairs = trading_pairs
        self.fitness = None

    @classmethod
    def create_random(cls, parameters, all_pairs, num_pairs):
        genes = []
        for param in parameters:
            if param['type'] == 'Int':
                value = random.randint(int(param['start']), int(param['end']))
            else:  # DecimalParameter
                value = random.uniform(param['start'] + 1e-10, param['end'] - 1e-10)
                value = round(value, param['decimal_places'])
            genes.append(value)
        trading_pairs = random.sample(all_pairs, num_pairs)
        return cls(genes, trading_pairs)

    def constrain_genes(self, parameters):
        for i, param in enumerate(parameters):
            if param['type'] == 'Int':
                self.genes[i] = int(max(param['start'], min(param['end'], self.genes[i])))
            else:  # DecimalParameter
                self.genes[i] = round(max(param['start'], min(param['end'], self.genes[i])), param['decimal_places'])

    # 在交叉和变异操作后调用此方法
    def after_genetic_operation(self, parameters):
        self.constrain_genes(parameters)

    def copy(self):
        return copy.deepcopy(self)

    def mutate_trading_pairs(self, all_pairs, mutation_rate):
        for i in range(len(self.trading_pairs)):
            if random.random() < mutation_rate:
                self.trading_pairs[i] = random.choice(all_pairs)

from typing import List
import random

class Individual:
    def __init__(self, genes: List[float]):
        self.genes = genes
        self.fitness = None

    @classmethod
    def create_random(cls, parameters):
        genes = []
        for param in parameters:
            if param['type'] == 'Int':
                value = random.randint(int(param['start']), int(param['end']))
            else:  # DecimalParameter
                value = random.uniform(param['start'] + 1e-10, param['end'] - 1e-10)
                value = round(value, param['decimal_places'])
            genes.append(value)
        return cls(genes)

    def constrain_genes(self, parameters):
        for i, param in enumerate(parameters):
            if param['type'] == 'Int':
                self.genes[i] = int(max(param['start'], min(param['end'], self.genes[i])))
            else:  # DecimalParameter
                self.genes[i] = round(max(param['start'], min(param['end'], self.genes[i])), param['decimal_places'])

    # 在交叉和变异操作后调用此方法
    def after_genetic_operation(self, parameters):
        self.constrain_genes(parameters)



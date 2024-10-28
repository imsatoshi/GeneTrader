from typing import List
import random
import copy

class Individual:
    def __init__(self, genes: List[float], trading_pairs: List[str], param_types: List[dict]):
        self.genes = genes
        self.trading_pairs = trading_pairs
        self.fitness = None
        self.param_types = param_types  # 添加参数类型信息

    @classmethod
    def create_random(cls, parameters, all_pairs, num_pairs):
        genes = []
        for param in parameters:
            if param['type'] == 'Int':
                value = random.randint(int(param['start']), int(param['end']))
            elif param['type'] == 'Decimal':
                value = random.uniform(param['start'] + 1e-10, param['end'] - 1e-10)
                value = round(value, param['decimal_places'])
            if param['type'] == 'Categorical':
                value = random.choice(param['options'])
            if param['type'] == 'Boolean':
                value = random.choice([True, False])
            genes.append(value)
        if num_pairs is not None:
            trading_pairs = random.sample(all_pairs, num_pairs)
        else:
            trading_pairs = all_pairs
        return cls(genes, trading_pairs, parameters)  # 传入 parameters

    def constrain_genes(self, parameters):
        for i, param in enumerate(parameters):
            if param['type'] == 'Int':
                self.genes[i] = int(max(param['start'], min(param['end'], self.genes[i])))
            if param['type'] == 'Decimal':
                self.genes[i] = round(max(param['start'], min(param['end'], self.genes[i])), param['decimal_places'])


    # 在交叉和变异操作后调用此方法
    def after_genetic_operation(self, parameters):
        self.constrain_genes(parameters)

    def copy(self):
        return copy.deepcopy(self)

    def mutate_trading_pairs(self, all_pairs, mutation_rate):
        # 创建一个集合来存储当前的交易对
        if self.trading_pairs is None:
            return
        current_pairs = set(self.trading_pairs)
        
        for i in range(len(self.trading_pairs)):
            if random.random() < mutation_rate:
                # 创建一个可选择的交易对列表，排除当前已有的交易对
                available_pairs = [pair for pair in all_pairs if pair not in current_pairs]
                
                if available_pairs:
                    # 从可用的交易对中随机选择一个
                    new_pair = random.choice(available_pairs)
                    
                    # 从当前集合中移除旧的交易对
                    current_pairs.remove(self.trading_pairs[i])
                    
                    # 添加新的交易对到集合和列表中
                    current_pairs.add(new_pair)
                    self.trading_pairs[i] = new_pair
                else:
                    # 如果没有可用的新交易对，保持原样
                    pass

        # 更新 self.trading_pairs 为新的列表（可选，因为我们是直接修改的列表）
        self.trading_pairs = list(current_pairs)

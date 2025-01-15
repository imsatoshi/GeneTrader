from typing import List
import random
import copy

class Individual:
    def __init__(self, genes: List[float], trading_pairs_index: List[str], param_types: List[dict]):
        self.genes = genes
        # self.trading_pairs = trading_pairs
        self.trading_pairs_index = trading_pairs_index
        self.fitness = None
        self.param_types = param_types

    @classmethod
    def create_random(cls, parameters, all_pairs, num_pairs):
        genes = []
        for param in parameters:
            if param['type'] == 'Int':
                if param.get('name') == 'max_open_trades':
                    min_value = max(1, int(param['start']))
                    value = random.randint(min_value, int(param['end']))
                else:
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
            trading_pairs_index = random.sample(range(len(all_pairs)), num_pairs)
        else:
            trading_pairs_index = range(len(all_pairs))
        return cls(genes, trading_pairs_index, parameters)

    def constrain_genes(self, parameters):
        for i, param in enumerate(parameters):
            if param['type'] == 'Int':
                if param.get('name') == 'max_open_trades':
                    min_value = max(1, int(param['start']))
                    self.genes[i] = int(max(min_value, min(param['end'], self.genes[i])))
                else:
                    self.genes[i] = int(max(param['start'], min(param['end'], self.genes[i])))
            if param['type'] == 'Decimal':
                self.genes[i] = round(max(param['start'], min(param['end'], self.genes[i])), param['decimal_places'])

    def after_genetic_operation(self, parameters):
        self.constrain_genes(parameters)

    def copy(self):
        return copy.deepcopy(self)

    def mutate_trading_pairs(self, all_pairs, mutation_rate):
        if self.trading_pairs_index is None:
            return
        
        all_pairs_index = range(len(all_pairs)) 
        
        current_pairs = set(self.trading_pairs_index)
        
        for i in range(len(self.trading_pairs_index)):
            if random.random() < mutation_rate:
                available_pairs = [pair for pair in all_pairs_index if pair not in current_pairs]
                
                if available_pairs:
                    new_pair = random.choice(available_pairs)
                    
                    current_pairs.remove(self.trading_pairs_index[i])
                    
                    current_pairs.add(new_pair)

        self.trading_pairs_index = list(current_pairs)

    def crossover_trading_pairs(self, other_individual, crossover_rate=0.5):
        """
        Perform crossover operation on trading pair indices between two individuals
        """
        # Create copies for children
        child1 = self.copy()
        child2 = other_individual.copy()
        
        if random.random() < crossover_rate and self.trading_pairs_index is not None:
            pairs_length = len(self.trading_pairs_index)
            if pairs_length != len(other_individual.trading_pairs_index):
                raise ValueError("Trading pairs index length mismatch")
                    
            crossover_point = random.randint(1, pairs_length - 1)
            
            # Perform crossover
            new_pairs_1 = list(dict.fromkeys(
                self.trading_pairs_index[:crossover_point] + 
                other_individual.trading_pairs_index[crossover_point:]
            ))
            new_pairs_2 = list(dict.fromkeys(
                other_individual.trading_pairs_index[:crossover_point] + 
                self.trading_pairs_index[crossover_point:]
            ))
            
            # Ensure both children have the correct number of pairs
            while len(new_pairs_1) < pairs_length:
                available_pairs = [p for p in self.trading_pairs_index + other_individual.trading_pairs_index 
                                 if p not in new_pairs_1]
                if available_pairs:
                    new_pairs_1.append(random.choice(available_pairs))
                else:
                    break
                
            while len(new_pairs_2) < pairs_length:
                available_pairs = [p for p in self.trading_pairs_index + other_individual.trading_pairs_index 
                                 if p not in new_pairs_2]
                if available_pairs:
                    new_pairs_2.append(random.choice(available_pairs))
                else:
                    break
            
            # If still not enough pairs, randomly select from all possible indices
            all_possible_indices = list(range(max(max(self.trading_pairs_index), 
                                                max(other_individual.trading_pairs_index)) + 1))
            
            while len(new_pairs_1) < pairs_length:
                available = [i for i in all_possible_indices if i not in new_pairs_1]
                if available:
                    new_pairs_1.append(random.choice(available))
            
            while len(new_pairs_2) < pairs_length:
                available = [i for i in all_possible_indices if i not in new_pairs_2]
                if available:
                    new_pairs_2.append(random.choice(available))
            
            # Trim if necessary
            new_pairs_1 = new_pairs_1[:pairs_length]
            new_pairs_2 = new_pairs_2[:pairs_length]
            
            child1.trading_pairs_index = new_pairs_1
            child2.trading_pairs_index = new_pairs_2
            
        return child1.trading_pairs_index, child2.trading_pairs_index
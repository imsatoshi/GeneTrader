import json
import os

class Settings:
    def __init__(self, config_file='ga.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        self.project_dir = self.config['project_dir']
        self.results_dir = os.path.join(self.project_dir, self.config['results_dir'])
        self.best_generations_dir = os.path.join(self.project_dir, self.config['best_generations_dir'])
        self.strategy_dir = self.config['strategy_dir']
        self.user_dir = self.config['user_dir']
        self.freqtrade_path = self.config['freqtrade_path']
        self.config_file = self.config['config_file']
        self.max_retries = self.config['max_retries']
        self.retry_delay = self.config['retry_delay']
        self.pool_processes = self.config['pool_processes']
        self.population_size = self.config['population_size']
        self.generations = self.config['generations']
        self.crossover_prob = self.config['crossover_prob']
        self.mutation_prob = self.config['mutation_prob']
        self.tournament_size = self.config['tournament_size']

        for key, value in self.config['proxy'].items():
            os.environ[f'{key}_proxy'] = value

settings = Settings()
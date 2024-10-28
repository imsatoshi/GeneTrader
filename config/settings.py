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
        self.data_dir = self.config['data_dir']  # Add this line
        self.base_strategy_file = self.config['base_strategy_file']
        self.backtest_timerange_weeks = self.config['backtest_timerange_weeks']
        self.num_pairs = self.config['num_pairs']
        self.checkpoint_dir = os.path.join(self.project_dir, self.config['checkpoint_dir'])
        self.checkpoint_frequency = self.config['checkpoint_frequency']
        self.add_max_open_trades = self.config['add_max_open_trades']
        self.fix_pairs = self.config['fix_pairs']
        self.add_dynamic_timeframes = self.config['add_dynamic_timeframes']
        for key, value in self.config['proxy'].items():
            os.environ[f'{key}_proxy'] = value


settings = Settings()
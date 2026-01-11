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
        self.data_dir = self.config['data_dir']
        self.base_strategy_file = self.config['base_strategy_file']
        self.backtest_timerange_weeks = self.config['backtest_timerange_weeks']
        self.num_pairs = self.config['num_pairs']
        self.checkpoint_dir = os.path.join(self.project_dir, self.config['checkpoint_dir'])
        self.checkpoint_frequency = self.config['checkpoint_frequency']
        self.add_max_open_trades = self.config['add_max_open_trades']
        self.fix_pairs = self.config['fix_pairs']
        self.add_dynamic_timeframes = self.config['add_dynamic_timeframes']
        self.diversity_threshold = self.config['diversity_threshold']
        self.max_mutation_prob = self.config['max_mutation_prob']
        self.bark_endpoint = self.config["bark_endpoint"]
        self.bark_key = self.config["bark_key"]
        self.hostname = self.config["hostname"]
        self.username = self.config["username"]
        self.port = self.config["port"]
        self.key_path = self.config["key_path"]
        self.remote_datadir = self.config["remote_datadir"]
        self.remote_strategydir = self.config["remote_strategydir"]
        self.api_url = self.config["api_url"]
        self.freqtrade_username = self.config["freqtrade_username"]
        self.freqtrade_password = self.config["freqtrade_password"]

        # Optuna optimizer settings (Issue #13)
        self.optimizer_type = self.config.get('optimizer_type', 'genetic')
        self.optuna_n_trials = self.config.get('optuna_n_trials', self.generations * self.population_size)
        self.optuna_sampler = self.config.get('optuna_sampler', 'tpe')
        self.optuna_n_startup_trials = self.config.get('optuna_n_startup_trials', 10)
        self.optuna_pruning = self.config.get('optuna_pruning', False)
        self.optuna_n_jobs = self.config.get('optuna_n_jobs', 1)

        # Set proxy environment variables
        for key, value in self.config.get('proxy', {}).items():
            os.environ[f'{key}_proxy'] = value


settings = Settings()
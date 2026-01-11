import json
import os
from typing import Any, Dict, List, Set


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class Settings:
    """Configuration settings loaded from JSON file with validation."""

    # Required configuration fields
    REQUIRED_FIELDS: Set[str] = {
        'project_dir', 'results_dir', 'best_generations_dir', 'strategy_dir',
        'user_dir', 'freqtrade_path', 'config_file', 'max_retries', 'retry_delay',
        'pool_processes', 'population_size', 'generations', 'crossover_prob',
        'mutation_prob', 'tournament_size', 'data_dir', 'base_strategy_file',
        'backtest_timerange_weeks', 'num_pairs', 'checkpoint_dir', 'checkpoint_frequency',
        'add_max_open_trades', 'fix_pairs', 'add_dynamic_timeframes',
        'diversity_threshold', 'max_mutation_prob'
    }

    # Fields with numeric constraints
    NUMERIC_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
        'population_size': {'min': 1, 'type': int},
        'generations': {'min': 1, 'type': int},
        'crossover_prob': {'min': 0.0, 'max': 1.0, 'type': float},
        'mutation_prob': {'min': 0.0, 'max': 1.0, 'type': float},
        'tournament_size': {'min': 1, 'type': int},
        'max_retries': {'min': 1, 'type': int},
        'retry_delay': {'min': 0, 'type': (int, float)},  # Delay in seconds
        'pool_processes': {'min': 1, 'type': int},
        'num_pairs': {'min': 1, 'type': int},
        'backtest_timerange_weeks': {'min': 1, 'type': int},
        'diversity_threshold': {'min': 0.0, 'max': 1.0, 'type': float},
        'max_mutation_prob': {'min': 0.0, 'max': 1.0, 'type': float},
        'checkpoint_frequency': {'min': 1, 'type': int},
    }

    def __init__(self, config_file: str = 'ga.json'):
        if not os.path.exists(config_file):
            raise ConfigurationError(f"Configuration file not found: {config_file}")

        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")

        self._validate_config()
        self._load_settings()

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Check required fields
        missing_fields = self.REQUIRED_FIELDS - set(self.config.keys())
        if missing_fields:
            raise ConfigurationError(f"Missing required config fields: {missing_fields}")

        # Validate numeric constraints
        errors = []
        for field, constraints in self.NUMERIC_CONSTRAINTS.items():
            if field not in self.config:
                continue
            value = self.config[field]
            expected_type = constraints.get('type', float)

            # Type check
            if not isinstance(value, (int, float)):
                errors.append(f"{field}: expected number, got {type(value).__name__}")
                continue

            # Range check
            if 'min' in constraints and value < constraints['min']:
                errors.append(f"{field}: value {value} is below minimum {constraints['min']}")
            if 'max' in constraints and value > constraints['max']:
                errors.append(f"{field}: value {value} is above maximum {constraints['max']}")

        if errors:
            raise ConfigurationError("Configuration validation errors:\n" + "\n".join(errors))

    def _load_settings(self) -> None:
        """Load settings from validated config."""
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


class _SettingsProxy:
    """Lazy loading proxy for settings to avoid import-time errors."""

    _instance = None

    def __getattr__(self, name):
        if _SettingsProxy._instance is None:
            config_file = os.environ.get('GENETRADER_CONFIG', 'ga.json')
            if os.path.exists(config_file):
                _SettingsProxy._instance = Settings(config_file)
            else:
                raise RuntimeError(
                    f"Configuration file '{config_file}' not found. "
                    "Please create it from ga.json.example or set GENETRADER_CONFIG environment variable."
                )
        return getattr(_SettingsProxy._instance, name)


# Use lazy loading proxy to avoid import-time errors when config file doesn't exist
settings = _SettingsProxy()
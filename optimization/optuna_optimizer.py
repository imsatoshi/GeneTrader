"""Optuna-based optimizer for strategy optimization.

This module provides Optuna optimization as an alternative to genetic algorithms,
which can be more efficient for large parameter spaces (Issue #13).
"""
import json
import gc
from typing import List, Tuple, Dict, Any, Optional
import multiprocessing

import optuna
from optuna.samplers import TPESampler, CmaEsSampler

from optimization.base_optimizer import BaseOptimizer
from genetic_algorithm.individual import Individual
from strategy.backtest import run_backtest
from utils.logging_config import logger


class OptunaOptimizer(BaseOptimizer):
    """
    Optuna-based optimizer using Tree-structured Parzen Estimator (TPE) or CMA-ES.

    This optimizer is more efficient than genetic algorithms when the search space
    is large, as it builds a probabilistic model of the objective function.
    """

    def __init__(self, settings: Any, parameters: List[Dict], all_pairs: List[str]):
        """
        Initialize the Optuna optimizer.

        Args:
            settings: Settings object containing optimization configuration
            parameters: List of parameter definitions for optimization
            all_pairs: List of all available trading pairs
        """
        super().__init__(settings, parameters)
        self.all_pairs = all_pairs
        self.best_individual: Optional[Individual] = None
        self.best_individuals: List[Tuple[int, Individual]] = []

        # Get Optuna-specific settings with defaults
        self.n_trials = getattr(settings, 'optuna_n_trials', settings.generations * settings.population_size)
        self.sampler_type = getattr(settings, 'optuna_sampler', 'tpe')
        self.n_startup_trials = getattr(settings, 'optuna_n_startup_trials', 10)
        self.pruning_enabled = getattr(settings, 'optuna_pruning', False)

    def _create_sampler(self) -> optuna.samplers.BaseSampler:
        """Create the appropriate sampler based on configuration."""
        if self.sampler_type == 'cmaes':
            return CmaEsSampler(n_startup_trials=self.n_startup_trials)
        else:  # default to TPE
            return TPESampler(n_startup_trials=self.n_startup_trials)

    def _suggest_parameters(self, trial: optuna.Trial) -> List[Any]:
        """
        Suggest parameter values for a trial based on parameter definitions.

        Args:
            trial: Optuna trial object

        Returns:
            List of suggested parameter values
        """
        genes = []
        for i, param in enumerate(self.parameters):
            param_name = param.get('name', f'param_{i}')

            if param['type'] == 'Int':
                if param_name == 'max_open_trades':
                    min_val = max(1, int(param['start']))
                else:
                    min_val = int(param['start'])
                value = trial.suggest_int(param_name, min_val, int(param['end']))

            elif param['type'] == 'Decimal':
                value = trial.suggest_float(
                    param_name,
                    param['start'],
                    param['end'],
                    step=10 ** (-param.get('decimal_places', 2))
                )

            elif param['type'] == 'Categorical':
                value = trial.suggest_categorical(param_name, param['options'])

            elif param['type'] == 'Boolean':
                value = trial.suggest_categorical(param_name, [True, False])
            else:
                # Default to float
                value = trial.suggest_float(param_name, param.get('start', 0), param.get('end', 1))

            genes.append(value)

        return genes

    def _suggest_trading_pairs(self, trial: optuna.Trial) -> List[str]:
        """
        Suggest trading pairs for a trial.

        Args:
            trial: Optuna trial object

        Returns:
            List of selected trading pairs
        """
        if self.settings.fix_pairs:
            return self.all_pairs

        # For dynamic pair selection, use categorical suggestions
        num_pairs = self.settings.num_pairs
        selected_pairs = []

        for i in range(num_pairs):
            available = [p for p in self.all_pairs if p not in selected_pairs]
            if available:
                pair = trial.suggest_categorical(f'pair_{i}', available)
                selected_pairs.append(pair)

        return selected_pairs if selected_pairs else self.all_pairs[:num_pairs]

    def _objective(self, trial: optuna.Trial, trial_number: int) -> float:
        """
        Objective function for Optuna optimization.

        Args:
            trial: Optuna trial object
            trial_number: The trial number for logging

        Returns:
            Fitness value (to be maximized)
        """
        # Suggest parameters
        genes = self._suggest_parameters(trial)

        # Suggest trading pairs
        trading_pairs = self._suggest_trading_pairs(trial)

        # Run backtest
        try:
            fitness = run_backtest(genes, trading_pairs, trial_number)

            if fitness is None:
                fitness = float('-inf')

            # Create individual and track if it's the best
            individual = Individual(genes, trading_pairs, self.parameters)
            individual.fitness = fitness

            # Update best individual
            if self.best_individual is None or fitness > self.best_individual.fitness:
                self.best_individual = individual

            # Store this trial's best
            self.best_individuals.append((trial_number, individual))

            logger.info(f"Trial {trial_number}: Fitness = {fitness:.6f}")

            # Cleanup
            gc.collect()

            return fitness

        except Exception as e:
            logger.error(f"Error in trial {trial_number}: {str(e)}")
            return float('-inf')

    def optimize(self, initial_individuals: List[Individual] = None) -> List[Tuple[int, Individual]]:
        """
        Run Optuna optimization.

        Args:
            initial_individuals: Optional list of initial individuals (used for warm start)

        Returns:
            List of tuples containing (trial number, best individual)
        """
        logger.info(f"Starting Optuna optimization with {self.n_trials} trials")
        logger.info(f"Using sampler: {self.sampler_type}")

        # Create study
        sampler = self._create_sampler()
        study = optuna.create_study(
            direction='maximize',
            sampler=sampler,
            study_name='genetrader_optimization'
        )

        # If we have initial individuals, enqueue them as initial trials
        if initial_individuals:
            for ind in initial_individuals:
                params = {}
                for i, param in enumerate(self.parameters):
                    param_name = param.get('name', f'param_{i}')
                    params[param_name] = ind.genes[i]
                study.enqueue_trial(params)
                logger.info(f"Enqueued initial individual with fitness: {ind.fitness}")

        # Run optimization with parallel evaluation if configured
        n_jobs = getattr(self.settings, 'optuna_n_jobs', 1)

        # Create wrapper for objective that includes trial number
        trial_counter = [0]
        def objective_wrapper(trial):
            trial_counter[0] += 1
            return self._objective(trial, trial_counter[0])

        study.optimize(
            objective_wrapper,
            n_trials=self.n_trials,
            n_jobs=n_jobs,
            show_progress_bar=True
        )

        # Log best result
        logger.info(f"Best trial: {study.best_trial.number}")
        logger.info(f"Best value: {study.best_value}")
        logger.info(f"Best params: {study.best_params}")

        # Filter to get best individuals per batch (similar to generations)
        batch_size = self.settings.population_size
        generation_bests = []

        for i in range(0, len(self.best_individuals), batch_size):
            batch = self.best_individuals[i:i + batch_size]
            if batch:
                best_in_batch = max(batch, key=lambda x: x[1].fitness if x[1].fitness is not None else float('-inf'))
                gen_num = (i // batch_size) + 1
                generation_bests.append((gen_num, best_in_batch[1]))

        return generation_bests if generation_bests else self.best_individuals

    def get_best_individual(self) -> Individual:
        """
        Get the best individual found during optimization.

        Returns:
            The best Individual found
        """
        return self.best_individual

    def get_study_statistics(self, study: optuna.Study) -> Dict[str, Any]:
        """
        Get statistics about the optimization study.

        Args:
            study: Optuna study object

        Returns:
            Dictionary containing study statistics
        """
        return {
            'n_trials': len(study.trials),
            'best_value': study.best_value,
            'best_params': study.best_params,
            'best_trial_number': study.best_trial.number,
            'n_complete_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
            'n_pruned_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
            'n_failed_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
        }

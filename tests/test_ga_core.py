"""Integration tests for the GA optimization loop.

This is the chain the whole project exists for — population -> parallel
backtest -> fitness -> selection — and it had one test before this file. Every
defect pinned here was live: a failed generation reusing the previous
generation's fitness, `--resume` accepting a flag it never honoured, and
walk-forward folds silently evaluating the same recent window.

`run_backtest` is patched throughout: real backtests shell out to Freqtrade.
"""

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from genetic_algorithm.individual import Individual
from optimization.genetic_optimizer import GeneticOptimizer

PARAMETERS = [
    {'name': 'buy_rsi', 'type': 'Int', 'start': 10, 'end': 40, 'optimize': True, 'default': 30},
    {'name': 'sell_rsi', 'type': 'Int', 'start': 60, 'end': 90, 'optimize': True, 'default': 70},
]
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']


def make_settings(tmpdir, **overrides):
    """Minimal settings object; pool_processes=1 keeps evaluation in-process."""
    base = dict(
        population_size=4, generations=3, tournament_size=2,
        crossover_prob=0.5, mutation_prob=0.2, max_mutation_prob=0.4,
        pool_processes=1, fix_pairs=True, num_pairs=2,
        checkpoint_dir=os.path.join(tmpdir, 'checkpoints'), checkpoint_frequency=1,
        enable_diversity_selection=False, diversity_selection_weight=0.3,
        diversity_threshold=0.1, backtest_timerange_weeks=12,
        max_drawdown_limit=0.35, min_profit_factor=1.0, min_win_rate=0.30,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class GACoreTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.settings = make_settings(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def optimizer(self, settings=None):
        return GeneticOptimizer(settings or self.settings, PARAMETERS, PAIRS)


class TestEvaluationLoop(GACoreTestCase):
    def test_optimize_returns_best_per_generation(self):
        with patch('optimization.genetic_optimizer.run_backtest', side_effect=lambda *a, **k: 1.5):
            results = self.optimizer().optimize()

        self.assertEqual(len(results), self.settings.generations)
        self.assertEqual([gen for gen, _ in results], [1, 2, 3])
        self.assertTrue(all(ind.fitness == 1.5 for _, ind in results))

    def test_none_fitness_becomes_negative_infinity(self):
        with patch('optimization.genetic_optimizer.run_backtest', return_value=None):
            results = self.optimizer().optimize()
        self.assertTrue(all(ind.fitness == float('-inf') for _, ind in results))

    def test_unexpected_error_does_not_reuse_previous_fitness(self):
        """A failed generation must not score new genes with old numbers.

        Individuals carry fitness through copy() and mutation, so an evaluation
        error that left fitness untouched allowed stale positive scores to pass
        the `fitness > 0` filter and drive selection.
        """
        calls = {'n': 0}

        def flaky(*args, **kwargs):
            calls['n'] += 1
            # Generation 1 (4 individuals) succeeds; generation 2 raises.
            if calls['n'] > self.settings.population_size:
                raise KeyError('unexpected worker failure')
            return 2.0

        optimizer = self.optimizer()
        with patch('optimization.genetic_optimizer.run_backtest', side_effect=flaky):
            results = optimizer.optimize()

        self.assertEqual(results[0][1].fitness, 2.0)
        for generation, individual in results[1:]:
            self.assertEqual(individual.fitness, float('-inf'),
                             f"generation {generation} kept a stale fitness")

    def test_os_error_marks_whole_generation_failed(self):
        with patch('optimization.genetic_optimizer.run_backtest', side_effect=OSError('pool died')):
            results = self.optimizer().optimize()
        self.assertTrue(all(ind.fitness == float('-inf') for _, ind in results))

    def test_timerange_is_forwarded_to_every_backtest(self):
        seen = []

        def capture(genes, pairs, generation, timerange, num_parameters):
            seen.append(timerange)
            return 1.0

        with patch('optimization.genetic_optimizer.run_backtest', side_effect=capture):
            self.optimizer().optimize(timerange='20240101-20240301')

        self.assertTrue(seen)
        self.assertEqual(set(seen), {'20240101-20240301'})

    def test_default_timerange_is_none(self):
        seen = []
        with patch('optimization.genetic_optimizer.run_backtest',
                   side_effect=lambda g, p, gen, tr, n: seen.append(tr) or 1.0):
            self.optimizer().optimize()
        self.assertEqual(set(seen), {None})


class TestCheckpointing(GACoreTestCase):
    def test_checkpoint_is_written_and_resumed(self):
        optimizer = self.optimizer()
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            optimizer.optimize()

        path = optimizer._checkpoint_path('ga_checkpoint')
        self.assertTrue(os.path.exists(path), 'no checkpoint written')

        # A resumed run starts past the checkpointed generation, so it performs
        # strictly fewer evaluations than a fresh run.
        settings = make_settings(self.temp_dir, generations=5)
        resumed = GeneticOptimizer(settings, PARAMETERS, PAIRS)
        calls = {'n': 0}

        def counting(*args, **kwargs):
            calls['n'] += 1
            return 1.0

        with patch('optimization.genetic_optimizer.run_backtest', side_effect=counting):
            results = resumed.optimize(resume=True)

        self.assertLess(calls['n'], 5 * settings.population_size)
        self.assertTrue(results)

    def test_resume_without_checkpoint_starts_fresh(self):
        optimizer = self.optimizer()
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            results = optimizer.optimize(resume=True)
        self.assertEqual(len(results), self.settings.generations)

    def test_checkpoint_with_mismatched_population_is_ignored(self):
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            self.optimizer().optimize()

        settings = make_settings(self.temp_dir, population_size=8)
        optimizer = GeneticOptimizer(settings, PARAMETERS, PAIRS)
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            results = optimizer.optimize(resume=True)

        self.assertEqual(len(results), settings.generations)

    def test_corrupt_checkpoint_does_not_crash(self):
        optimizer = self.optimizer()
        os.makedirs(self.settings.checkpoint_dir, exist_ok=True)
        with open(optimizer._checkpoint_path('ga_checkpoint'), 'wb') as f:
            f.write(b'not a pickle')

        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            results = optimizer.optimize(resume=True)
        self.assertEqual(len(results), self.settings.generations)

    def test_clear_checkpoint_removes_file(self):
        optimizer = self.optimizer()
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            optimizer.optimize()
        optimizer.clear_checkpoint()
        self.assertFalse(os.path.exists(optimizer._checkpoint_path('ga_checkpoint')))
        optimizer.clear_checkpoint()  # idempotent

    def test_checkpointing_disabled_writes_nothing(self):
        optimizer = self.optimizer()
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            optimizer.optimize(checkpoint_name=None)
        self.assertFalse(os.path.exists(optimizer._checkpoint_path('ga_checkpoint')))


class TestWalkForwardWiring(GACoreTestCase):
    """Folds must train on their own window, not the default recent one."""

    def test_each_fold_uses_its_own_training_timerange(self):
        settings = make_settings(
            self.temp_dir, generations=1, enable_walk_forward=True,
            walk_forward_method='rolling', walk_forward_train_weeks=8,
            walk_forward_test_weeks=2, walk_forward_min_train_weeks=4,
            total_data_weeks=16,
        )
        optimizer = GeneticOptimizer(settings, PARAMETERS, PAIRS)
        seen = []

        def capture(genes, pairs, generation, timerange, num_parameters):
            seen.append(timerange)
            return 1.0

        with patch('optimization.genetic_optimizer.run_backtest', side_effect=capture):
            _, validation = optimizer.optimize_with_walk_forward()

        self.assertGreater(validation.get('num_folds', 0), 0)
        self.assertNotIn(None, seen, 'a fold fell back to the default window')
        self.assertGreater(len(set(seen)), 1, 'every fold used the same timerange')

    def test_fold_runs_do_not_share_a_checkpoint(self):
        settings = make_settings(
            self.temp_dir, generations=1, enable_walk_forward=True,
            walk_forward_train_weeks=8, walk_forward_test_weeks=2,
            walk_forward_min_train_weeks=4, total_data_weeks=16,
        )
        optimizer = GeneticOptimizer(settings, PARAMETERS, PAIRS)
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            optimizer.optimize_with_walk_forward()

        self.assertFalse(os.path.exists(optimizer._checkpoint_path('ga_checkpoint')))


class TestSeedingAndBest(GACoreTestCase):
    def test_initial_individuals_are_seeded(self):
        seed = Individual.create_random(PARAMETERS, PAIRS, 2)
        with patch('optimization.genetic_optimizer.run_backtest', return_value=1.0):
            optimizer = self.optimizer()
            optimizer.optimize(initial_individuals=[seed])
        self.assertIsNotNone(optimizer.get_best_individual())

    def test_best_individual_tracks_highest_fitness(self):
        scores = iter([1.0, 2.0, 9.0, 1.0] + [0.5] * 20)
        with patch('optimization.genetic_optimizer.run_backtest',
                   side_effect=lambda *a, **k: next(scores, 0.5)):
            optimizer = self.optimizer()
            optimizer.optimize()
        self.assertEqual(optimizer.get_best_individual().fitness, 9.0)


if __name__ == '__main__':
    unittest.main()

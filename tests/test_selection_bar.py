"""Tests for the GA selection bar.

The failure this guards against is a false pass: a bar computed over a pool
that still contains disqualification codes and impossible backtests reports
that the winner cleared it, when the winner is one of those artifacts.
"""

import math
import os
import sys
import unittest

from strategy.selection_bar import (
    DISQUALIFIED_ABOVE,
    compute,
    expected_max,
    from_fitnesses,
    is_degenerate,
    scoreable,
)


def real(fitness, **overrides):
    """A record that looks like a genuine evaluated strategy."""
    record = {'fitness': fitness, 'max_drawdown': 0.12,
              'profit_factor': 1.4, 'win_rate': 0.55}
    record.update(overrides)
    return record


def degenerate(fitness):
    """Freqtrade's no-losing-trade signature."""
    return {'fitness': fitness, 'max_drawdown': 0.0,
            'profit_factor': 0.0, 'win_rate': 1.0}


class TestExpectedMax(unittest.TestCase):
    def test_more_trials_raises_the_bar(self):
        bars = [expected_max(n, 1.0) for n in (10, 100, 1000)]
        self.assertEqual(bars, sorted(bars))

    def test_scales_linearly_with_dispersion(self):
        self.assertAlmostEqual(expected_max(100, 2.0), 2 * expected_max(100, 1.0), places=9)

    def test_degenerate_inputs_return_zero(self):
        self.assertEqual(expected_max(1, 1.0), 0.0)
        self.assertEqual(expected_max(0, 1.0), 0.0)
        self.assertEqual(expected_max(100, 0.0), 0.0)

    def test_matches_reference_value(self):
        # Bailey / Lopez de Prado false-strategy benchmark, n=320, sd=1.
        self.assertAlmostEqual(expected_max(320, 1.0), 2.914, places=2)


class TestFiltering(unittest.TestCase):
    def test_disqualification_codes_are_dropped(self):
        # fitness_function returns -1.0 .. -4.0 as rejection codes.
        pool = [real(0.3), real(0.2)] + [real(code) for code in (-1.0, -2.0, -3.0, -4.0)]
        self.assertEqual(len(scoreable(pool)), 2)

    def test_non_finite_fitness_is_dropped(self):
        pool = [real(0.3), real(float('-inf')), real(float('nan')), real(0.2)]
        self.assertEqual(len(scoreable(pool)), 2)

    def test_boundary_of_disqualification(self):
        self.assertEqual(len(scoreable([real(DISQUALIFIED_ABOVE + 0.001), real(0.1)])), 2)
        self.assertEqual(len(scoreable([real(-1.0), real(0.1)])), 1)

    def test_degenerate_signature(self):
        self.assertTrue(is_degenerate(degenerate(0.5)))
        self.assertFalse(is_degenerate(real(0.5)))
        # All three conditions are required.
        self.assertFalse(is_degenerate({'fitness': 0.5, 'max_drawdown': 0.0,
                                        'profit_factor': 2.0, 'win_rate': 1.0}))
        self.assertFalse(is_degenerate({'fitness': 0.5, 'max_drawdown': 0.1,
                                        'profit_factor': 0.0, 'win_rate': 1.0}))

    def test_records_without_metrics_are_kept(self):
        # Fitness-only pools cannot be checked for degeneracy; keep them.
        self.assertEqual(len(scoreable([{'fitness': 0.3}, {'fitness': 0.4}])), 2)

    def test_degenerate_filtering_can_be_disabled(self):
        pool = [real(0.3), degenerate(0.9), real(0.2)]
        self.assertEqual(len(scoreable(pool)), 2)
        self.assertEqual(len(scoreable(pool, drop_degenerate=False)), 3)


class TestCompute(unittest.TestCase):
    def test_returns_none_when_too_few_survive(self):
        self.assertIsNone(compute([]))
        self.assertIsNone(compute([real(0.5)]))
        self.assertIsNone(compute([real(-1.0), real(-2.0), real(0.3)]))

    def test_counts_are_reported(self):
        pool = [real(0.3), real(0.2), real(-1.0), degenerate(0.9)]
        result = compute(pool)
        self.assertEqual(result.n_evaluated, 4)
        self.assertEqual(result.n_scored, 2)
        self.assertEqual(result.n_dropped, 2)

    def test_winner_excludes_filtered_entries(self):
        result = compute([real(0.3), real(0.2), degenerate(0.99)])
        self.assertAlmostEqual(result.winner, 0.3)

    def test_bar_is_mean_plus_expected_max(self):
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = from_fitnesses(values)
        import statistics
        expected = statistics.mean(values) + expected_max(5, statistics.pstdev(values))
        self.assertAlmostEqual(result.bar, expected, places=9)
        self.assertAlmostEqual(result.edge, result.winner - result.bar, places=9)

    def test_n_trials_override_raises_the_bar(self):
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        small = from_fitnesses(values)
        large = from_fitnesses(values, n_trials=10000)
        self.assertGreater(large.bar, small.bar)
        self.assertLess(large.edge, small.edge)

    def test_an_outlier_winner_clears_the_bar(self):
        result = from_fitnesses([0.10, 0.11, 0.12, 0.13, 0.14, 5.0])
        self.assertTrue(result.clears_bar)
        self.assertGreater(result.edge, 0)

    def test_an_evenly_spread_population_has_no_standout(self):
        # The top of a smooth ramp is roughly what chance produces at this n.
        result = from_fitnesses([0.10 + 0.01 * i for i in range(30)])
        self.assertFalse(result.clears_bar)

    def test_an_identical_population_never_clears(self):
        result = from_fitnesses([0.2] * 11)
        self.assertEqual(result.dispersion, 0.0)
        self.assertFalse(result.clears_bar)


class TestDegeneratesCauseFalsePass(unittest.TestCase):
    """The regression this module exists for.

    Impossible backtests raise both the winner and the spread. Leaving them in
    can turn a winner that sits below its own selection bar into one that
    appears to clear it -- exactly the reassurance an overfitting check must
    never manufacture.
    """

    def setUp(self):
        # Artifacts interleave with the real population rather than sitting in
        # a block above it, which is how they appear in real logs: they raise
        # the winner more than they raise the bar.
        self.pool = ([real(0.02 + 0.38 * i / 29) for i in range(30)]
                     + [degenerate(0.07 + 0.53 * i / 7) for i in range(8)])

    def test_verdict_flips_when_artifacts_are_included(self):
        honest = compute(self.pool)
        inflated = compute(self.pool, drop_degenerate=False)

        self.assertFalse(honest.clears_bar)
        self.assertTrue(inflated.clears_bar)
        self.assertGreater(inflated.winner, honest.winner)
        self.assertGreater(inflated.dispersion, honest.dispersion)

    def test_honest_winner_is_a_real_candidate(self):
        honest = compute(self.pool)
        best_real = max(r['fitness'] for r in self.pool if not is_degenerate(r))
        self.assertAlmostEqual(honest.winner, best_real)

    def test_summary_names_the_direction(self):
        self.assertIn('BELOW', compute(self.pool).summary())
        self.assertIn('above', compute(self.pool, drop_degenerate=False).summary())


class TestAgainstCommittedLog(unittest.TestCase):
    """Regression against the fitness log committed in daily_results/.

    That run predates the anti-overfitting disqualifications added later, so a
    quarter of its pool is backtests that reported no losing trade. It is the
    concrete case this filtering exists for.
    """

    LOG = os.path.join(os.path.dirname(__file__), '..',
                       'daily_results', '20241223', 'gen10', 'fitness_info.txt')

    def setUp(self):
        if not os.path.exists(self.LOG):
            self.skipTest('committed fitness log not present')
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from selection_bar import parse_log
        self.records = parse_log(self.LOG)

    def test_log_parses(self):
        self.assertGreater(len(self.records), 100)

    def test_a_quarter_of_the_pool_is_degenerate(self):
        share = sum(1 for r in self.records if is_degenerate(r)) / len(self.records)
        self.assertGreater(share, 0.2)

    def test_the_reported_winner_was_an_artifact(self):
        overall_best = max(self.records, key=lambda r: r['fitness'])
        self.assertTrue(is_degenerate(overall_best))

    def test_filtering_reverses_the_verdict(self):
        honest = compute(self.records)
        inflated = compute(self.records, drop_degenerate=False)
        self.assertTrue(inflated.clears_bar)
        self.assertFalse(honest.clears_bar)


if __name__ == '__main__':
    unittest.main()

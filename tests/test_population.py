"""Unit tests for genetic_algorithm/population.py."""
import unittest
from unittest.mock import patch, MagicMock

from genetic_algorithm.population import Population
from genetic_algorithm.individual import Individual


class TestPopulation(unittest.TestCase):
    """Test cases for Population class."""

    def setUp(self):
        """Set up test fixtures."""
        # Parameters should be a list of dicts with all required fields
        self.sample_params = [
            {'name': 'param1', 'type': 'Int', 'start': 1, 'end': 10, 'default': 5, 'decimal_places': 0},
            {'name': 'param2', 'type': 'Decimal', 'start': 0.1, 'end': 1.0, 'default': 0.5, 'decimal_places': 2},
        ]
        self.sample_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    def _create_individual(self, genes, pairs):
        """Helper to create an individual with proper param_types."""
        return Individual(genes=genes, trading_pairs=pairs, param_types=self.sample_params)

    def test_init(self):
        """Test population initialization."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        pop = Population([ind1, ind2])

        self.assertEqual(len(pop.individuals), 2)
        self.assertEqual(pop.individuals[0], ind1)
        self.assertEqual(pop.individuals[1], ind2)

    def test_create_random(self):
        """Test random population creation."""
        pop = Population.create_random(
            size=5,
            parameters=self.sample_params,
            trading_pairs=self.sample_pairs,
            num_pairs=2
        )

        self.assertEqual(len(pop), 5)
        for ind in pop:
            self.assertEqual(len(ind.genes), 2)
            self.assertEqual(len(ind.trading_pairs), 2)

    def test_create_random_all_pairs(self):
        """Test population creation with all trading pairs."""
        pop = Population.create_random(
            size=3,
            parameters=self.sample_params,
            trading_pairs=self.sample_pairs,
            num_pairs=None
        )

        self.assertEqual(len(pop), 3)
        for ind in pop:
            self.assertEqual(len(ind.trading_pairs), len(self.sample_pairs))

    def test_get_best(self):
        """Test getting best individual."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind1.fitness = 0.5
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        ind2.fitness = 0.8
        ind3 = self._create_individual([3, 0.3], ['SOL/USDT'])
        ind3.fitness = 0.3

        pop = Population([ind1, ind2, ind3])
        best = pop.get_best()

        self.assertEqual(best, ind2)
        self.assertEqual(best.fitness, 0.8)

    def test_get_best_with_none_fitness(self):
        """Test get_best handles None fitness values."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind1.fitness = None
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        ind2.fitness = 0.5
        ind3 = self._create_individual([3, 0.3], ['SOL/USDT'])
        ind3.fitness = None

        pop = Population([ind1, ind2, ind3])
        best = pop.get_best()

        self.assertEqual(best, ind2)

    def test_get_best_all_none_fitness(self):
        """Test get_best when all individuals have None fitness."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind1.fitness = None
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        ind2.fitness = None

        pop = Population([ind1, ind2])
        # Should return one of them (implementation returns max by -inf)
        best = pop.get_best()
        self.assertIn(best, [ind1, ind2])

    def test_get_best_empty_population_raises(self):
        """Test get_best raises ValueError for empty population."""
        pop = Population([])
        with self.assertRaises(ValueError):
            pop.get_best()

    def test_len(self):
        """Test __len__ method."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        pop = Population([ind1, ind2])

        self.assertEqual(len(pop), 2)

    def test_len_empty(self):
        """Test __len__ for empty population."""
        pop = Population([])
        self.assertEqual(len(pop), 0)

    def test_iter(self):
        """Test __iter__ method."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        pop = Population([ind1, ind2])

        individuals_list = list(pop)
        self.assertEqual(len(individuals_list), 2)
        self.assertEqual(individuals_list[0], ind1)
        self.assertEqual(individuals_list[1], ind2)

    def test_iter_empty(self):
        """Test iteration over empty population."""
        pop = Population([])
        self.assertEqual(list(pop), [])

    def test_get_best_negative_fitness(self):
        """Test get_best with negative fitness values."""
        ind1 = self._create_individual([5, 0.5], ['BTC/USDT'])
        ind1.fitness = -0.5
        ind2 = self._create_individual([7, 0.7], ['ETH/USDT'])
        ind2.fitness = -0.1
        ind3 = self._create_individual([3, 0.3], ['SOL/USDT'])
        ind3.fitness = -0.8

        pop = Population([ind1, ind2, ind3])
        best = pop.get_best()

        self.assertEqual(best, ind2)  # -0.1 is the highest


class TestPopulationEdgeCases(unittest.TestCase):
    """Edge case tests for Population class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_params = [
            {'name': 'p1', 'type': 'Int', 'start': 1, 'end': 10, 'default': 5}
        ]

    def _create_individual(self, genes, pairs):
        """Helper to create an individual with proper param_types."""
        return Individual(genes=genes, trading_pairs=pairs, param_types=self.sample_params)

    def test_single_individual_population(self):
        """Test population with single individual."""
        ind = self._create_individual([5], ['BTC/USDT'])
        ind.fitness = 0.5
        pop = Population([ind])

        self.assertEqual(len(pop), 1)
        self.assertEqual(pop.get_best(), ind)

    def test_create_random_single_size(self):
        """Test creating population of size 1."""
        pop = Population.create_random(
            size=1,
            parameters=self.sample_params,
            trading_pairs=['BTC/USDT'],
            num_pairs=1
        )

        self.assertEqual(len(pop), 1)

    def test_individuals_are_independent(self):
        """Test that random individuals are independent copies."""
        pop = Population.create_random(
            size=2,
            parameters=self.sample_params,
            trading_pairs=['BTC/USDT', 'ETH/USDT'],
            num_pairs=1
        )

        # Modifying one should not affect the other
        pop.individuals[0].fitness = 1.0
        self.assertIsNone(pop.individuals[1].fitness)


if __name__ == '__main__':
    unittest.main()

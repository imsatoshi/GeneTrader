"""Unit tests for Individual class."""
import unittest
from genetic_algorithm.individual import Individual


class TestIndividual(unittest.TestCase):
    """Test cases for Individual class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parameters = [
            {'name': 'param1', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True},
            {'name': 'param2', 'type': 'Decimal', 'start': 0.0, 'end': 1.0, 'decimal_places': 2, 'optimize': True},
            {'name': 'param3', 'type': 'Boolean', 'optimize': True},
            {'name': 'param4', 'type': 'Categorical', 'options': ['a', 'b', 'c'], 'optimize': True},
        ]
        self.all_pairs = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'SOL/USDT']

    def test_create_random_individual(self):
        """Test creating a random individual."""
        ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)

        self.assertEqual(len(ind.genes), 4)
        self.assertEqual(len(ind.trading_pairs), 2)
        self.assertIsNone(ind.fitness)

    def test_create_random_int_parameter(self):
        """Test that Int parameters are within bounds."""
        for _ in range(10):
            ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)
            self.assertGreaterEqual(ind.genes[0], 0)
            self.assertLessEqual(ind.genes[0], 100)
            self.assertIsInstance(ind.genes[0], int)

    def test_create_random_decimal_parameter(self):
        """Test that Decimal parameters are within bounds."""
        for _ in range(10):
            ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)
            self.assertGreaterEqual(ind.genes[1], 0.0)
            self.assertLessEqual(ind.genes[1], 1.0)
            self.assertIsInstance(ind.genes[1], float)

    def test_create_random_boolean_parameter(self):
        """Test that Boolean parameters are valid."""
        ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)
        self.assertIsInstance(ind.genes[2], bool)

    def test_create_random_categorical_parameter(self):
        """Test that Categorical parameters are from options."""
        ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)
        self.assertIn(ind.genes[3], ['a', 'b', 'c'])

    def test_create_random_all_pairs(self):
        """Test creating individual with all trading pairs."""
        ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=None)
        self.assertEqual(len(ind.trading_pairs), 4)

    def test_constrain_genes(self):
        """Test gene constraint functionality."""
        ind = Individual([150, 2.0, True, 'a'], self.all_pairs[:2], self.parameters)
        ind.constrain_genes(self.parameters)

        self.assertEqual(ind.genes[0], 100)  # Should be clamped to max
        self.assertEqual(ind.genes[1], 1.0)  # Should be clamped to max

    def test_copy(self):
        """Test deep copy functionality."""
        ind = Individual.create_random(self.parameters, self.all_pairs, num_pairs=2)
        ind.fitness = 100.0

        ind_copy = ind.copy()

        self.assertEqual(ind.genes, ind_copy.genes)
        self.assertEqual(ind.trading_pairs, ind_copy.trading_pairs)
        self.assertEqual(ind.fitness, ind_copy.fitness)

        # Verify it's a deep copy
        ind_copy.genes[0] = -999
        self.assertNotEqual(ind.genes[0], ind_copy.genes[0])

    def test_mutate_trading_pairs(self):
        """Test trading pair mutation."""
        ind = Individual([50, 0.5, True, 'a'], ['BTC/USDT', 'ETH/USDT'], self.parameters)
        original_pairs = ind.trading_pairs.copy()

        # With mutation rate 1.0, all pairs should potentially change
        ind.mutate_trading_pairs(self.all_pairs, mutation_rate=1.0)

        # Should still have same number of pairs
        self.assertEqual(len(ind.trading_pairs), 2)
        # All pairs should be from all_pairs
        for pair in ind.trading_pairs:
            self.assertIn(pair, self.all_pairs)

    def test_mutate_trading_pairs_no_mutation(self):
        """Test trading pair mutation with rate 0."""
        ind = Individual([50, 0.5, True, 'a'], ['BTC/USDT', 'ETH/USDT'], self.parameters)
        original_pairs = set(ind.trading_pairs)

        ind.mutate_trading_pairs(self.all_pairs, mutation_rate=0.0)

        # Pairs should be unchanged
        self.assertEqual(set(ind.trading_pairs), original_pairs)


class TestIndividualEdgeCases(unittest.TestCase):
    """Test edge cases for Individual class."""

    def test_unknown_parameter_type(self):
        """Test that unknown parameter types raise ValueError."""
        parameters = [{'name': 'unknown', 'type': 'Unknown', 'optimize': True}]
        with self.assertRaises(ValueError):
            Individual.create_random(parameters, ['BTC/USDT'], num_pairs=1)

    def test_empty_trading_pairs(self):
        """Test mutation with empty trading pairs."""
        parameters = [{'name': 'param', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True}]
        ind = Individual([50], [], parameters)

        # Should not raise
        ind.mutate_trading_pairs(['BTC/USDT'], mutation_rate=1.0)


if __name__ == '__main__':
    unittest.main()

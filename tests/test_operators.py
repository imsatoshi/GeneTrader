"""Unit tests for genetic algorithm operators."""
import unittest
from genetic_algorithm.individual import Individual
from genetic_algorithm.operators import crossover, mutate, select_tournament


class TestCrossover(unittest.TestCase):
    """Test cases for crossover operator."""

    def setUp(self):
        """Set up test fixtures."""
        self.parameters = [
            {'name': 'p1', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True},
            {'name': 'p2', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True},
            {'name': 'p3', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True},
        ]
        self.parent1 = Individual([10, 20, 30], ['BTC/USDT', 'ETH/USDT'], self.parameters)
        self.parent2 = Individual([40, 50, 60], ['XRP/USDT', 'SOL/USDT'], self.parameters)

    def test_crossover_creates_two_children(self):
        """Test that crossover produces two children."""
        child1, child2 = crossover(self.parent1, self.parent2)

        self.assertIsInstance(child1, Individual)
        self.assertIsInstance(child2, Individual)

    def test_crossover_preserves_gene_count(self):
        """Test that children have same number of genes as parents."""
        child1, child2 = crossover(self.parent1, self.parent2)

        self.assertEqual(len(child1.genes), len(self.parent1.genes))
        self.assertEqual(len(child2.genes), len(self.parent2.genes))

    def test_crossover_with_pairs(self):
        """Test crossover with trading pair crossover."""
        child1, child2 = crossover(self.parent1, self.parent2, with_pair=True)

        # Children should have trading pairs
        self.assertTrue(len(child1.trading_pairs) > 0)
        self.assertTrue(len(child2.trading_pairs) > 0)

    def test_crossover_without_pairs(self):
        """Test crossover without trading pair crossover."""
        child1, child2 = crossover(self.parent1, self.parent2, with_pair=False)

        # Children should have parent's trading pairs
        self.assertEqual(child1.trading_pairs, self.parent1.trading_pairs)
        self.assertEqual(child2.trading_pairs, self.parent2.trading_pairs)

    def test_crossover_single_gene(self):
        """Test crossover with single gene (edge case)."""
        params = [{'name': 'p1', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True}]
        p1 = Individual([10], ['BTC/USDT'], params)
        p2 = Individual([20], ['ETH/USDT'], params)

        child1, child2 = crossover(p1, p2)

        # Should return copies since can't crossover with 1 gene
        self.assertEqual(len(child1.genes), 1)
        self.assertEqual(len(child2.genes), 1)


class TestMutate(unittest.TestCase):
    """Test cases for mutation operator."""

    def setUp(self):
        """Set up test fixtures."""
        self.parameters = [
            {'name': 'int_param', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True},
            {'name': 'dec_param', 'type': 'Decimal', 'start': 0.0, 'end': 1.0, 'decimal_places': 2, 'optimize': True},
            {'name': 'bool_param', 'type': 'Boolean', 'optimize': True},
            {'name': 'cat_param', 'type': 'Categorical', 'options': ['a', 'b', 'c'], 'optimize': True},
        ]

    def test_mutate_with_zero_rate(self):
        """Test that zero mutation rate doesn't change genes."""
        ind = Individual([50, 0.5, True, 'a'], ['BTC/USDT'], self.parameters)
        original_genes = ind.genes.copy()

        mutate(ind, mutation_rate=0.0)

        self.assertEqual(ind.genes, original_genes)

    def test_mutate_preserves_gene_count(self):
        """Test that mutation preserves number of genes."""
        ind = Individual([50, 0.5, True, 'a'], ['BTC/USDT'], self.parameters)

        mutate(ind, mutation_rate=0.5)

        self.assertEqual(len(ind.genes), 4)

    def test_mutate_int_stays_in_range(self):
        """Test that mutated Int values stay within bounds."""
        params = [{'name': 'p', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True}]
        ind = Individual([50], ['BTC/USDT'], params)

        for _ in range(100):
            mutate(ind, mutation_rate=1.0)
            self.assertGreaterEqual(ind.genes[0], 0)
            self.assertLessEqual(ind.genes[0], 100)

    def test_mutate_decimal_stays_in_range(self):
        """Test that mutated Decimal values stay within bounds."""
        params = [{'name': 'p', 'type': 'Decimal', 'start': 0.0, 'end': 1.0, 'decimal_places': 2, 'optimize': True}]
        ind = Individual([0.5], ['BTC/USDT'], params)

        for _ in range(100):
            mutate(ind, mutation_rate=1.0)
            self.assertGreaterEqual(ind.genes[0], 0.0)
            self.assertLessEqual(ind.genes[0], 1.0)

    def test_mutate_categorical_stays_in_options(self):
        """Test that mutated Categorical values are from options."""
        params = [{'name': 'p', 'type': 'Categorical', 'options': ['x', 'y', 'z'], 'optimize': True}]
        ind = Individual(['x'], ['BTC/USDT'], params)

        for _ in range(20):
            mutate(ind, mutation_rate=1.0)
            self.assertIn(ind.genes[0], ['x', 'y', 'z'])


class TestSelectTournament(unittest.TestCase):
    """Test cases for tournament selection."""

    def setUp(self):
        """Set up test fixtures."""
        params = [{'name': 'p', 'type': 'Int', 'start': 0, 'end': 100, 'optimize': True}]
        self.population = []
        for i in range(10):
            ind = Individual([i * 10], ['BTC/USDT'], params)
            ind.fitness = float(i * 10)  # Fitness = gene value
            self.population.append(ind)

    def test_select_returns_individual(self):
        """Test that selection returns an Individual."""
        selected = select_tournament(self.population, tournament_size=3)
        self.assertIsInstance(selected, Individual)

    def test_select_returns_from_population(self):
        """Test that selected individual is from population."""
        selected = select_tournament(self.population, tournament_size=3)
        self.assertIn(selected, self.population)

    def test_select_tournament_size_one(self):
        """Test selection with tournament size 1."""
        selected = select_tournament(self.population, tournament_size=1)
        self.assertIn(selected, self.population)

    def test_select_empty_population_raises(self):
        """Test that empty population raises ValueError."""
        with self.assertRaises(ValueError):
            select_tournament([], tournament_size=3)

    def test_select_large_tournament(self):
        """Test selection with tournament size larger than population."""
        selected = select_tournament(self.population, tournament_size=100)
        # Should handle gracefully and return best from entire population
        self.assertEqual(selected.fitness, 90.0)  # Best fitness is 90


if __name__ == '__main__':
    unittest.main()

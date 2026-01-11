"""Unit tests for utils/fitness_helpers.py."""
import unittest
import tempfile
import os

from utils.fitness_helpers import (
    extract_fitness,
    extract_final_fitness,
    extract_generation,
    extract_strategy_name,
    extract_win_rate,
    parse_fitness_log,
    get_best_strategy
)


class TestExtractFitness(unittest.TestCase):
    """Tests for extract_fitness function."""

    def test_extract_valid_fitness(self):
        """Test extraction of valid fitness value."""
        line = "Generation 1, Strategy: GeneTrader_001, Fitness: 1.234"
        result = extract_fitness(line)
        self.assertEqual(result, 1.234)

    def test_extract_negative_fitness(self):
        """Test extraction of negative fitness value."""
        line = "Fitness: -0.567"
        result = extract_fitness(line)
        self.assertEqual(result, -0.567)

    def test_extract_no_fitness(self):
        """Test extraction when no fitness present."""
        line = "Generation 1 completed"
        result = extract_fitness(line)
        self.assertIsNone(result)

    def test_extract_fitness_with_spaces(self):
        """Test extraction with variable spacing."""
        line = "Fitness:   2.5"
        result = extract_fitness(line)
        self.assertEqual(result, 2.5)


class TestExtractFinalFitness(unittest.TestCase):
    """Tests for extract_final_fitness function."""

    def test_extract_final_fitness(self):
        """Test extraction of final fitness value."""
        line = "Final Fitness: 3.456"
        result = extract_final_fitness(line)
        self.assertEqual(result, 3.456)

    def test_fallback_to_regular_fitness(self):
        """Test fallback to regular fitness extraction."""
        line = "Fitness: 1.234"
        result = extract_final_fitness(line)
        self.assertEqual(result, 1.234)

    def test_no_fitness_found(self):
        """Test when no fitness is found."""
        line = "No fitness here"
        result = extract_final_fitness(line)
        self.assertIsNone(result)


class TestExtractGeneration(unittest.TestCase):
    """Tests for extract_generation function."""

    def test_extract_valid_generation(self):
        """Test extraction of generation number."""
        line = "Generation 5 started"
        result = extract_generation(line)
        self.assertEqual(result, 5)

    def test_extract_no_generation(self):
        """Test extraction when no generation present."""
        line = "Fitness evaluation complete"
        result = extract_generation(line)
        self.assertIsNone(result)

    def test_extract_large_generation(self):
        """Test extraction of large generation number."""
        line = "Generation 1000"
        result = extract_generation(line)
        self.assertEqual(result, 1000)


class TestExtractStrategyName(unittest.TestCase):
    """Tests for extract_strategy_name function."""

    def test_extract_valid_strategy(self):
        """Test extraction of strategy name."""
        line = "Strategy: GeneTrader_001, Fitness: 1.0"
        result = extract_strategy_name(line)
        self.assertEqual(result, "GeneTrader_001,")

    def test_extract_no_strategy(self):
        """Test extraction when no strategy present."""
        line = "Generation 1 complete"
        result = extract_strategy_name(line)
        self.assertIsNone(result)


class TestExtractWinRate(unittest.TestCase):
    """Tests for extract_win_rate function."""

    def test_extract_valid_win_rate(self):
        """Test extraction of win rate."""
        line = "Win Rate: 0.65"
        result = extract_win_rate(line)
        self.assertEqual(result, 0.65)

    def test_extract_no_win_rate(self):
        """Test extraction when no win rate present."""
        line = "Fitness: 1.0"
        result = extract_win_rate(line)
        self.assertIsNone(result)

    def test_extract_whole_number_win_rate(self):
        """Test extraction of whole number win rate."""
        line = "Win Rate: 1"
        result = extract_win_rate(line)
        self.assertEqual(result, 1.0)


class TestParseFitnessLog(unittest.TestCase):
    """Tests for parse_fitness_log function."""

    def test_parse_valid_log(self):
        """Test parsing a valid fitness log."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Generation 1\n")
            f.write("Strategy: Test1, Fitness: 1.5\n")
            f.write("Generation 2\n")
            f.write("Strategy: Test2, Fitness: 2.5\n")
            f.write("Strategy: Test3, Fitness: 2.0\n")
            f.name

        try:
            result = parse_fitness_log(f.name)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[1]['max_fitness'], 1.5)
            self.assertEqual(result[2]['max_fitness'], 2.5)
        finally:
            os.unlink(f.name)

    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        result = parse_fitness_log('/nonexistent/path/file.txt')
        self.assertEqual(result, {})

    def test_parse_empty_log(self):
        """Test parsing an empty log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            f.name

        try:
            result = parse_fitness_log(f.name)
            self.assertEqual(result, {})
        finally:
            os.unlink(f.name)


class TestGetBestStrategy(unittest.TestCase):
    """Tests for get_best_strategy function."""

    def test_get_best_from_generations(self):
        """Test finding best strategy across generations."""
        generations = {
            1: {'max_fitness': 1.0, 'strategy_name': 'Strat1', 'max_fitness_line': ''},
            2: {'max_fitness': 3.0, 'strategy_name': 'Strat2', 'max_fitness_line': ''},
            3: {'max_fitness': 2.0, 'strategy_name': 'Strat3', 'max_fitness_line': ''},
        }
        fitness, strategy, gen = get_best_strategy(generations)
        self.assertEqual(fitness, 3.0)
        self.assertEqual(strategy, 'Strat2')
        self.assertEqual(gen, 2)

    def test_get_best_empty_generations(self):
        """Test with empty generations dict."""
        fitness, strategy, gen = get_best_strategy({})
        self.assertEqual(fitness, float('-inf'))
        self.assertIsNone(strategy)
        self.assertIsNone(gen)

    def test_get_best_with_none_fitness(self):
        """Test with some None fitness values."""
        generations = {
            1: {'max_fitness': None, 'strategy_name': 'Strat1', 'max_fitness_line': ''},
            2: {'max_fitness': 2.0, 'strategy_name': 'Strat2', 'max_fitness_line': ''},
        }
        fitness, strategy, gen = get_best_strategy(generations)
        self.assertEqual(fitness, 2.0)
        self.assertEqual(strategy, 'Strat2')
        self.assertEqual(gen, 2)


class TestPrecompiledPatterns(unittest.TestCase):
    """Tests to verify patterns are pre-compiled at module level."""

    def test_patterns_exist(self):
        """Test that pre-compiled patterns exist."""
        from utils import fitness_helpers
        self.assertTrue(hasattr(fitness_helpers, '_PATTERN_FITNESS'))
        self.assertTrue(hasattr(fitness_helpers, '_PATTERN_GENERATION'))
        self.assertTrue(hasattr(fitness_helpers, '_PATTERN_STRATEGY_NAME'))
        self.assertTrue(hasattr(fitness_helpers, '_PATTERN_WIN_RATE'))
        self.assertTrue(hasattr(fitness_helpers, '_PATTERN_FINAL_FITNESS'))

    def test_patterns_are_compiled(self):
        """Test that patterns are compiled regex objects."""
        import re
        from utils import fitness_helpers
        self.assertIsInstance(fitness_helpers._PATTERN_FITNESS, re.Pattern)
        self.assertIsInstance(fitness_helpers._PATTERN_GENERATION, re.Pattern)


if __name__ == '__main__':
    unittest.main()

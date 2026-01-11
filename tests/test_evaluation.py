"""Unit tests for strategy evaluation module."""
import unittest
import tempfile
import os
import math
from unittest.mock import patch, MagicMock

from strategy.evaluation import (
    extract_win_rate,
    parse_backtest_results,
    fitness_function,
    _parse_duration,
    _extract_value_from_pattern,
    _PATTERNS,
    _empty_results
)


class TestExtractWinRate(unittest.TestCase):
    """Test cases for extract_win_rate function."""

    def test_extract_win_rate_from_valid_content(self):
        """Test extracting win rate from valid backtest output."""
        # Format: The win rate is extracted as parts[-2].split()[3] / 100
        # parts[-2] would be the second-to-last cell separated by │
        content = """
│ Pair       │ Entries │ Avg Profit │ Tot Profit │ Tot Profit % │ Avg Duration │ Win  Draw  Loss  Win% │
│------------│---------│------------│------------│--------------│--------------│-----------------------│
│ BTC/USDT   │     100 │      2.50% │    250.00  │        25.00 │     02:30:00 │   60    10    30   60 │
│ TOTAL      │     100 │      2.50% │    250.00  │        25.00 │     02:30:00 │   65    10    25   65 │
"""
        result = extract_win_rate(content)
        self.assertEqual(result, 0.65)

    def test_extract_win_rate_no_total(self):
        """Test extracting win rate when TOTAL line is missing."""
        content = "Some content without TOTAL line"
        result = extract_win_rate(content)
        self.assertEqual(result, 0.0)

    def test_extract_win_rate_invalid_format(self):
        """Test extracting win rate from malformed content."""
        content = "TOTAL │ invalid │ data"
        result = extract_win_rate(content)
        self.assertEqual(result, 0.0)


class TestParseDuration(unittest.TestCase):
    """Test cases for _parse_duration function."""

    def test_parse_simple_duration(self):
        """Test parsing simple time duration."""
        result = _parse_duration("2:30:00")
        self.assertEqual(result, 150)  # 2 hours 30 minutes

    def test_parse_duration_with_days(self):
        """Test parsing duration with days."""
        result = _parse_duration("1 day, 2:30:00")
        self.assertEqual(result, 1590)  # 1 day + 2 hours 30 minutes

    def test_parse_duration_multiple_days(self):
        """Test parsing duration with multiple days."""
        result = _parse_duration("3 days, 0:00:00")
        self.assertEqual(result, 4320)  # 3 days in minutes

    def test_parse_empty_duration(self):
        """Test parsing empty duration."""
        result = _parse_duration("")
        self.assertEqual(result, 0)

    def test_parse_zero_duration(self):
        """Test parsing zero duration."""
        result = _parse_duration("0:00:00")
        self.assertEqual(result, 0)

    def test_parse_invalid_duration(self):
        """Test parsing invalid duration string."""
        result = _parse_duration("invalid")
        self.assertEqual(result, 0)


class TestExtractValueFromPattern(unittest.TestCase):
    """Test cases for _extract_value_from_pattern function."""

    def test_extract_numeric_value(self):
        """Test extracting numeric value."""
        content = "Sharpe │ 2.45"
        result = _extract_value_from_pattern(_PATTERNS['sharpe_ratio'], content)
        self.assertEqual(result, 2.45)

    def test_extract_negative_value(self):
        """Test extracting negative value."""
        content = "Absolute profit │ -125.50 USDT"
        result = _extract_value_from_pattern(_PATTERNS['absolute_profit'], content)
        self.assertEqual(result, -125.50)

    def test_extract_string_value(self):
        """Test extracting string value."""
        content = "Avg. Duration Winners │ 2:30:00 │"
        result = _extract_value_from_pattern(
            _PATTERNS['avg_duration_winners'], content,
            default='0:00:00', is_string=True
        )
        self.assertEqual(result, "2:30:00")

    def test_extract_missing_value(self):
        """Test extracting when pattern not found."""
        content = "Some other content"
        result = _extract_value_from_pattern(_PATTERNS['sharpe_ratio'], content, default=0.0)
        self.assertEqual(result, 0.0)


class TestEmptyResults(unittest.TestCase):
    """Test cases for _empty_results function."""

    def test_empty_results_structure(self):
        """Test that empty results has all expected keys."""
        result = _empty_results()
        expected_keys = {
            'total_profit_usdt', 'total_profit_percent', 'win_rate',
            'max_drawdown', 'sharpe_ratio', 'sortino_ratio', 'profit_factor',
            'avg_profit', 'total_trades', 'daily_avg_trades', 'avg_trade_duration'
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_empty_results_values(self):
        """Test that all empty results values are zero."""
        result = _empty_results()
        for key, value in result.items():
            self.assertEqual(value, 0, f"{key} should be 0")


class TestParseBacktestResults(unittest.TestCase):
    """Test cases for parse_backtest_results function."""

    def setUp(self):
        """Create sample backtest result content."""
        self.valid_content = """
========================================================== SUMMARY METRICS ===========================================================
│          Metric │                     Value │
│----------------┼--------------------------│
│ Absolute profit │                123.45 USDT │
│ Total profit %  │                  12.35%    │
│ Max % of account underwater │        5.25%  │
│ Sharpe          │                    1.85    │
│ Sortino         │                    2.15    │
│ Profit factor   │                    1.65    │
│ Total/Daily Avg Trades │         100 / 3.5  │
│ Avg. Duration Winners │         2:30:00     │
│ TOTAL │ 100 │ 2.5 │ 75 │
"""

    def test_parse_valid_results(self):
        """Test parsing valid backtest results."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.valid_content)
            temp_path = f.name

        try:
            result = parse_backtest_results(temp_path)
            self.assertEqual(result['total_profit_usdt'], 123.45)
            self.assertAlmostEqual(result['total_profit_percent'], 0.1235, places=4)
            self.assertAlmostEqual(result['max_drawdown'], 0.0525, places=4)
            self.assertEqual(result['sharpe_ratio'], 1.85)
            self.assertEqual(result['sortino_ratio'], 2.15)
            self.assertEqual(result['profit_factor'], 1.65)
            self.assertEqual(result['total_trades'], 100)
            self.assertAlmostEqual(result['daily_avg_trades'], 3.5, places=1)
        finally:
            os.unlink(temp_path)

    def test_parse_no_summary_metrics(self):
        """Test parsing file without SUMMARY METRICS."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("No summary metrics here")
            temp_path = f.name

        try:
            result = parse_backtest_results(temp_path)
            self.assertEqual(result, _empty_results())
        finally:
            os.unlink(temp_path)

    def test_parse_file_not_found(self):
        """Test parsing non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            parse_backtest_results("/nonexistent/path/file.txt")


class TestFitnessFunction(unittest.TestCase):
    """Test cases for fitness_function."""

    def setUp(self):
        """Set up test fixtures."""
        self.good_results = {
            'total_profit_percent': 0.50,  # 50% profit
            'win_rate': 0.95,
            'max_drawdown': 0.05,
            'sharpe_ratio': 2.0,
            'sortino_ratio': 2.5,
            'profit_factor': 2.0,
            'daily_avg_trades': 3.5,
            'avg_trade_duration': 720  # 12 hours
        }
        self.bad_results = {
            'total_profit_percent': -0.20,  # -20% loss
            'win_rate': 0.30,
            'max_drawdown': 0.50,
            'sharpe_ratio': 0.5,
            'sortino_ratio': 0.5,
            'profit_factor': 0.5,
            'daily_avg_trades': 0.5,
            'avg_trade_duration': 10000  # Too long
        }

    @patch('strategy.evaluation.open', create=True)
    @patch('strategy.evaluation.logger')
    def test_good_results_higher_fitness(self, mock_logger, mock_open):
        """Test that good results produce higher fitness than bad results."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()

        good_fitness = fitness_function(self.good_results, 1, "TestStrategy", "1h")
        bad_fitness = fitness_function(self.bad_results, 1, "TestStrategy", "1h")

        self.assertGreater(good_fitness, bad_fitness)

    @patch('strategy.evaluation.open', create=True)
    @patch('strategy.evaluation.logger')
    def test_fitness_non_negative(self, mock_logger, mock_open):
        """Test that fitness is typically non-negative for reasonable inputs."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()

        fitness = fitness_function(self.good_results, 1, "TestStrategy", "1h")
        self.assertGreaterEqual(fitness, 0)

    @patch('strategy.evaluation.open', create=True)
    @patch('strategy.evaluation.logger')
    def test_fitness_with_zero_values(self, mock_logger, mock_open):
        """Test fitness function handles zero values gracefully."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock()

        zero_results = _empty_results()
        zero_results['avg_trade_duration'] = 0
        zero_results['daily_avg_trades'] = 0

        # Should not raise any exceptions
        fitness = fitness_function(zero_results, 1, "TestStrategy", "1h")
        self.assertIsInstance(fitness, float)


class TestRegexPatterns(unittest.TestCase):
    """Test that pre-compiled regex patterns are valid."""

    def test_all_patterns_compile(self):
        """Test that all patterns are compiled regex objects."""
        import re
        for name, pattern in _PATTERNS.items():
            self.assertIsInstance(pattern, re.Pattern, f"{name} should be a compiled pattern")

    def test_patterns_have_capture_groups(self):
        """Test that all patterns have at least one capture group."""
        for name, pattern in _PATTERNS.items():
            self.assertGreaterEqual(pattern.groups, 1, f"{name} should have capture groups")


if __name__ == '__main__':
    unittest.main()

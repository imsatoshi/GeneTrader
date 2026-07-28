"""Evaluation functions for backtest result parsing and fitness calculation.

This module provides functions to parse Freqtrade backtest results and
calculate fitness scores for the genetic algorithm optimization.
"""
import sys
import os
import math
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import re
from typing import Dict, Any, Union, Optional
from utils.logging_config import logger
from config.config import LOG_CONFIG, PROJECT_ROOT
from config.settings import settings


# Pre-compiled regex patterns for better performance
# These patterns are used repeatedly in parse_backtest_results
_PATTERNS = {
    'absolute_profit': re.compile(r'Absolute profit\s*│\s*([-\d.]+)\s*USDT', re.IGNORECASE),
    'total_profit_percent': re.compile(r'Total profit %\s*│\s*([\d.-]+)%', re.IGNORECASE),
    'max_drawdown': re.compile(r'Max % of account underwater\s*│\s*([\d.]+)%', re.IGNORECASE),
    'sharpe_ratio': re.compile(r'Sharpe\s*│\s*([\d.]+)', re.IGNORECASE),
    'sortino_ratio': re.compile(r'Sortino\s*│\s*([\d.]+)', re.IGNORECASE),
    'profit_factor': re.compile(r'Profit factor\s*│\s*([\d.]+)', re.IGNORECASE),
    'avg_profit': re.compile(r'│\s*TOTAL\s*│.*?│\s*([\d.-]+)\s*│', re.DOTALL | re.IGNORECASE),
    'total_trades': re.compile(r'Total/Daily Avg Trades\s*│\s*(\d+)\s*/', re.IGNORECASE),
    'daily_avg_trades': re.compile(r'Total/Daily Avg Trades\s*│\s*\d+\s*/\s*([\d.]+)', re.IGNORECASE),
    'avg_duration_winners': re.compile(r'Avg\. Duration Winners\s*│\s*(.*?)\s*│', re.DOTALL | re.IGNORECASE),
}

def extract_win_rate(content: str) -> float:
    # Find the line containing 'TOTAL'
    total_line = None
    for line in content.split('\n'):
        if 'TOTAL' in line:
            total_line = line
            break

    if total_line:
        # Split the line and extract the win rate
        parts = [p.strip() for p in total_line.split('│')]
        try:
            win_rate = float(parts[-2].split()[3]) / 100  # Convert percentage to decimal
            return win_rate
        except (IndexError, ValueError) as e:
            logger.error(f"Error extracting win rate: {str(e)}")
            return 0.0

    return 0.0


def _extract_value_from_pattern(pattern: re.Pattern, content: str,
                                 default: Union[float, str] = 0,
                                 is_string: bool = False) -> Union[float, str]:
    """Extract a value using a pre-compiled regex pattern.

    Args:
        pattern: Pre-compiled regex pattern
        content: Content string to search
        default: Default value if pattern not found
        is_string: If True, return string value; otherwise convert to float

    Returns:
        Extracted value or default
    """
    match = pattern.search(content)
    if match:
        value = match.group(1).strip()
        if is_string:
            return value
        try:
            return float(value)
        except ValueError:
            logger.error(f"Could not convert to float: {value}")
            return default
    return default


def _parse_duration(duration_str: str) -> int:
    """Parse duration string to total minutes.

    Args:
        duration_str: Duration string like "1 day, 2:30:00" or "2:30:00"

    Returns:
        Total duration in minutes
    """
    if not duration_str or duration_str == '0:00:00':
        return 0

    parts = duration_str.split(', ')
    total_minutes = 0

    try:
        for part in parts:
            if 'day' in part:
                total_minutes += int(part.split()[0]) * 24 * 60
            else:
                time_parts = part.split(':')
                if len(time_parts) >= 2:
                    total_minutes += int(time_parts[0]) * 60 + int(time_parts[1])
    except (ValueError, IndexError) as e:
        logger.warning(f"Error parsing duration '{duration_str}': {e}")
        return 0

    return total_minutes


def _empty_results() -> Dict[str, Any]:
    """Return empty results dictionary with default values."""
    return {
        'total_profit_usdt': 0,
        'total_profit_percent': 0,
        'win_rate': 0,
        'max_drawdown': 0,
        'sharpe_ratio': 0,
        'sortino_ratio': 0,
        'profit_factor': 0,
        'avg_profit': 0,
        'total_trades': 0,
        'daily_avg_trades': 0,
        'avg_trade_duration': 0
    }


def parse_backtest_results(file_path: str) -> Dict[str, Any]:
    """Parse backtest results from a Freqtrade output file.

    Args:
        file_path: Path to the backtest results file

    Returns:
        Dictionary containing parsed metrics

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If the file cannot be read
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"Backtest results file not found: {file_path}")
        raise
    except IOError as e:
        logger.error(f"Error reading backtest results file {file_path}: {e}")
        raise

    if "SUMMARY METRICS" not in content:
        logger.warning(f"{file_path} does not contain summary metrics. No trades were executed.")
        return _empty_results()

    # Use pre-compiled patterns for better performance
    duration_str = _extract_value_from_pattern(
        _PATTERNS['avg_duration_winners'], content, default='0:00:00', is_string=True
    )

    parsed_result = {
        'total_profit_usdt': _extract_value_from_pattern(_PATTERNS['absolute_profit'], content),
        'total_profit_percent': _extract_value_from_pattern(_PATTERNS['total_profit_percent'], content) / 100,
        'win_rate': extract_win_rate(content),
        'max_drawdown': _extract_value_from_pattern(_PATTERNS['max_drawdown'], content) / 100,
        'sharpe_ratio': _extract_value_from_pattern(_PATTERNS['sharpe_ratio'], content),
        'sortino_ratio': _extract_value_from_pattern(_PATTERNS['sortino_ratio'], content),
        'profit_factor': _extract_value_from_pattern(_PATTERNS['profit_factor'], content),
        'avg_profit': _extract_value_from_pattern(_PATTERNS['avg_profit'], content),
        'total_trades': _extract_value_from_pattern(_PATTERNS['total_trades'], content),
        'daily_avg_trades': _extract_value_from_pattern(_PATTERNS['daily_avg_trades'], content),
        'avg_trade_duration': _parse_duration(duration_str)
    }

    return parsed_result

def fitness_function(parsed_result: Dict[str, Any], generation: int,
                     strategy_name: str, timeframe: str,
                     num_parameters: int = 0,
                     backtest_weeks: int = 30) -> float:
    """Calculate fitness score for a trading strategy based on backtest results.

    This fitness function is designed to PREVENT OVERFITTING by:
    1. Requiring minimum trade counts for statistical significance
    2. Penalizing excessive drawdown (>35% = disqualified)
    3. Requiring minimum profit factor (>=1.0) and win rate (>=30%)
    4. Including complexity penalty for too many parameters
    5. Balancing profit with risk-adjusted metrics

    Args:
        parsed_result: Dictionary of parsed backtest metrics
        generation: Current generation number
        strategy_name: Name of the strategy being evaluated
        timeframe: Trading timeframe (e.g., "1h", "4h")
        num_parameters: Number of strategy parameters (for complexity penalty)
        backtest_weeks: Number of weeks in backtest period

    Returns:
        Fitness score as a float (higher is better, negative = disqualified)
    """
    # Extract relevant metrics
    total_profit_percent = parsed_result['total_profit_percent']
    win_rate = parsed_result['win_rate']
    max_drawdown = parsed_result['max_drawdown']
    sharpe_ratio = parsed_result['sharpe_ratio']
    sortino_ratio = parsed_result['sortino_ratio']
    profit_factor = parsed_result['profit_factor']
    daily_avg_trades = parsed_result['daily_avg_trades']
    avg_trade_duration = parsed_result['avg_trade_duration']
    total_trades = parsed_result['total_trades']

    # =========================================
    # DISQUALIFICATION CHECKS (Anti-Overfitting)
    # =========================================
    # Thresholds come from ga.json (max_drawdown_limit / min_profit_factor /
    # min_win_rate) so tightening them in config actually changes which
    # candidates survive, instead of only affecting live monitoring.
    max_drawdown_limit = getattr(settings, 'max_drawdown_limit', 0.35)
    min_profit_factor = getattr(settings, 'min_profit_factor', 1.0)
    min_win_rate = getattr(settings, 'min_win_rate', 0.30)

    # 1. Minimum trade count for statistical significance
    min_trades = max(backtest_weeks // 2, 15)
    if total_trades < min_trades:
        logger.warning(f"Strategy {strategy_name}: Insufficient trades ({total_trades} < {min_trades})")
        return -1.0

    # 2. Maximum drawdown limit (too risky)
    if max_drawdown > max_drawdown_limit:
        logger.warning(
            f"Strategy {strategy_name}: Excessive drawdown "
            f"({max_drawdown:.1%} > {max_drawdown_limit:.1%})"
        )
        return -2.0

    # 3. Minimum profit factor (must be profitable on average)
    if profit_factor < min_profit_factor:
        logger.warning(
            f"Strategy {strategy_name}: Unprofitable "
            f"(PF={profit_factor:.2f} < {min_profit_factor:.2f})"
        )
        return -3.0

    # 4. Minimum win rate (avoid extreme strategies)
    if win_rate < min_win_rate:
        logger.warning(
            f"Strategy {strategy_name}: Win rate too low "
            f"({win_rate:.1%} < {min_win_rate:.1%})"
        )
        return -4.0

    # =========================================
    # COMPONENT SCORES
    # =========================================

    # 1. Profit component (smooth transformation)
    profit_score = math.tanh(total_profit_percent / 2.0)

    # 2. Win rate component (target: 50-70% is optimal, not 90%)
    win_rate_target = 0.55
    win_rate_score = math.exp(-((win_rate - win_rate_target) ** 2) / 0.08)

    # 3. Risk-adjusted returns (critical for avoiding overfitting)
    sharpe_component = math.tanh(sharpe_ratio / 2) if sharpe_ratio > 0 else -0.5
    sortino_component = math.tanh(sortino_ratio / 2) if sortino_ratio > 0 else -0.5
    pf_component = math.tanh((profit_factor - 1) / 2) if profit_factor > 1 else -0.5

    risk_adjusted_score = (
        sharpe_component * 0.4 +
        sortino_component * 0.4 +
        pf_component * 0.2
    )

    # 4. Drawdown penalty (exponential decay)
    drawdown_penalty = math.exp(-3 * max_drawdown)

    # 5. Trade frequency score (prefer 1-4 trades per day)
    optimal_trades = 2.0
    trade_frequency_score = math.exp(-((daily_avg_trades - optimal_trades) ** 2) / 8)

    # 6. Trade duration score
    optimal_duration = 720  # 12 hours in minutes
    duration_score = math.exp(-((avg_trade_duration - optimal_duration) ** 2) / (2 * optimal_duration ** 2))

    # 7. Complexity penalty (penalize too many parameters)
    if num_parameters > 0:
        complexity_penalty = math.exp(-0.1 * max(0, num_parameters - 5))
    else:
        complexity_penalty = 1.0

    # 8. Statistical significance bonus
    trade_confidence = min(1.0, 0.5 + 0.5 * (total_trades - min_trades) / max(1, 100 - min_trades))

    # =========================================
    # COMBINED FITNESS (Balanced Weights)
    # =========================================
    fitness = (
        profit_score * 0.25 +           # Profit is important but not dominant
        win_rate_score * 0.10 +         # Reasonable win rate
        risk_adjusted_score * 0.25 +    # Risk-adjusted returns are critical
        drawdown_penalty * 0.15 +       # Penalize high drawdown
        trade_frequency_score * 0.10 +  # Reasonable trading frequency
        duration_score * 0.05 +         # Trade duration as minor factor
        trade_confidence * 0.10         # Statistical significance
    ) * complexity_penalty

    # Log the fitness components and final score
    log_message = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                   f"Strategy: {strategy_name}, "
                   f"Timeframe: {timeframe}, "
                   f"Generation: {generation}, "
                   f"Total Profit %: {total_profit_percent:.4f}, Profit Score: {profit_score:.4f}, "
                   f"Win Rate: {win_rate:.4f}, Win Rate Score: {win_rate_score:.4f}, "
                   f"Sharpe Ratio: {sharpe_ratio:.4f}, Sortino Ratio: {sortino_ratio:.4f}, Profit Factor: {profit_factor:.4f}, "
                   f"Risk-Adjusted Score: {risk_adjusted_score:.4f}, "
                   f"Max Drawdown: {max_drawdown:.4f}, Drawdown Penalty: {drawdown_penalty:.4f}, "
                   f"Daily Avg Trades: {daily_avg_trades:.2f}, Trade Frequency Score: {trade_frequency_score:.4f}, "
                   f"Avg Trade Duration (min): {avg_trade_duration:.2f}, Duration Score: {duration_score:.4f}, "
                   f"Total Trades: {int(total_trades)}, Trade Confidence: {trade_confidence:.4f}, "
                   f"Complexity Penalty: {complexity_penalty:.4f}, "
                   f"Final Fitness: {fitness:.4f}")

    # Write to log file
    log_path = os.path.join(LOG_CONFIG['log_dir'], LOG_CONFIG['fitness_log'])
    with open(log_path, 'a') as log_file:
        log_file.write(log_message + '\n')
    
    logger.info(log_message)
    logger.info(f"Log appended to: {log_path}")

    return fitness

def process_results_directory(directory_path: str) -> None:
    """Process all backtest result files in a directory and print win rates.

    Args:
        directory_path: Path to directory containing backtest result files
    """
    if not os.path.isdir(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        return

    for filename in os.listdir(directory_path):
        if filename.startswith("backtest_results_") and filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                win_rate = extract_win_rate(content)
                print(f"File: {filename}, Win Rate: {win_rate:.2%}")
            except IOError as e:
                logger.error(f"Error reading {filename}: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python evaluation.py <path_to_results_file>")
        print("       python evaluation.py --dir <path_to_results_directory>")
        sys.exit(1)

    if sys.argv[1] == "--dir" and len(sys.argv) >= 3:
        process_results_directory(sys.argv[2])
    else:
        file_path = sys.argv[1]
        try:
            parsed_results = parse_backtest_results(file_path)
            print("Parsed Results:")
            for key, value in parsed_results.items():
                print(f"  {key}: {value}")
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
    
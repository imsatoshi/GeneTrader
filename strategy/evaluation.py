import re
from typing import Dict
from utils.logging_config import logger

def parse_backtest_results(output_file: str) -> Dict[str, float]:
    with open(output_file, 'r') as f:
        content = f.read()

    if "SUMMARY METRICS" not in content:
        logger.warning(f"{output_file} does not contain summary metrics. No trades were executed.")
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

    def extract_value(pattern: str, default: float = 0, is_string: bool = False) -> float:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if is_string:
                return value
            try:
                return float(value)
            except ValueError:
                logger.error(f"Could not convert to float: {value}")
                return default
        else:
            return default

    def parse_duration(duration_str: str) -> int:
        parts = duration_str.split(', ')
        total_minutes = 0
        for part in parts:
            if 'day' in part:
                total_minutes += int(part.split()[0]) * 24 * 60
            else:
                time_parts = part.split(':')
                total_minutes += int(time_parts[0]) * 60 + int(time_parts[1])
        return total_minutes

    parsed_result = {
        'total_profit_usdt': extract_value(r'Absolute profit\s*│\s*([-\d.]+)\s*USDT'),
        'total_profit_percent': extract_value(r'Total profit %\s*│\s*([\d.-]+)%') / 100,
        'win_rate': extract_value(r'│\s*TOTAL\s*│.*?│.*?│.*?│.*?│.*?│.*?(\d+(?:\.\d+)?)\s*│') / 100,
        'max_drawdown': extract_value(r'Max % of account underwater\s*│\s*([\d.]+)%') / 100,
        'sharpe_ratio': extract_value(r'Sharpe\s*│\s*([\d.]+)'),
        'sortino_ratio': extract_value(r'Sortino\s*│\s*([\d.]+)'),
        'profit_factor': extract_value(r'Profit factor\s*│\s*([\d.]+)'),
        'avg_profit': extract_value(r'Avg Profit %\s*([\d.-]+)'),
        'total_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*(\d+)\s*/'),
        'daily_avg_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*\d+\s*/\s*([\d.]+)'),
        'avg_trade_duration': parse_duration(extract_value(r'Avg\. Duration Winners\s*│\s*(.*?)\s*│', default='0:00:00', is_string=True))
    }

    return parsed_result

def fitness_function(parsed_result: Dict[str, float]) -> float:
    sortino = parsed_result['sortino_ratio']
    profit = parsed_result['total_profit_percent']
    trade_count = parsed_result['total_trades']
    avg_profit = parsed_result['avg_profit']
    avg_duration = parsed_result['avg_trade_duration']

    if trade_count < 10:
        return float('-inf')  # Heavily penalize low trade count

    # Adjust fitness based on average trade duration
    duration_factor = min(avg_duration / 1440, 1)  # Cap at 1 day (1440 minutes)
    fitness = sortino + avg_profit * 0.1 + duration_factor

    if profit <= 0:
        fitness = fitness / 2

    return fitness
import sys
import os
import math
from datetime import datetime

# 将项目根目录添加到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import re
from typing import Dict, Any
from utils.logging_config import logger
from config.config import LOG_CONFIG, PROJECT_ROOT

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


def parse_backtest_results(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r') as f:
        content = f.read()

    if "SUMMARY METRICS" not in content:
        logger.warning(f"{file_path} does not contain summary metrics. No trades were executed.")
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

    # print(content)
    
    parsed_result = {
        'total_profit_usdt': extract_value(r'Absolute profit\s*│\s*([-\d.]+)\s*USDT'),
        'total_profit_percent': extract_value(r'Total profit %\s*│\s*([\d.-]+)%') * 1.0 / 100,
        'win_rate': extract_win_rate(content),
        'max_drawdown': extract_value(r'Max % of account underwater\s*│\s*([\d.]+)%') / 100,
        'sharpe_ratio': extract_value(r'Sharpe\s*│\s*([\d.]+)'),
        'sortino_ratio': extract_value(r'Sortino\s*│\s*([\d.]+)'),
        'profit_factor': extract_value(r'Profit factor\s*│\s*([\d.]+)'),
        'avg_profit': extract_value(r'│\s*TOTAL\s*│.*?│\s*([\d.-]+)\s*│', default=0),  # Updated pattern
        'total_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*(\d+)\s*/'),
        'daily_avg_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*\d+\s*/\s*([\d.]+)'),
        'avg_trade_duration': parse_duration(extract_value(r'Avg\. Duration Winners\s*│\s*(.*?)\s*│', default='0:00:00', is_string=True))
    }

    return parsed_result

def fitness_function(parsed_result: Dict[str, Any], generation: int, strategy_name: str, timeframe: str) -> float:
    # Extract relevant metrics
    total_profit_percent = parsed_result['total_profit_percent']
    win_rate = parsed_result['win_rate']
    max_drawdown = parsed_result['max_drawdown']
    sharpe_ratio = parsed_result['sharpe_ratio']
    sortino_ratio = parsed_result['sortino_ratio']
    profit_factor = parsed_result['profit_factor']
    daily_avg_trades = parsed_result['daily_avg_trades']
    avg_trade_duration = parsed_result['avg_trade_duration']

    # 1. Profit component (non-linear transformation with better scaling)
    profit_score = math.tanh(total_profit_percent / 2.0)  # 放宽收益区间

    # 2. Win rate component (more reasonable target)
    win_rate_score = 1 / (1 + math.exp(-10 * (win_rate - 0.9)))  

    # 3. Risk-adjusted returns (combining multiple metrics)
    risk_adjusted_score = (
        math.tanh(sharpe_ratio / 2) * 0.4 +  # Sharpe ratio
        math.tanh(sortino_ratio / 2) * 0.4 +  # Sortino ratio
        math.tanh(profit_factor / 3) * 0.2    # Profit factor
    )

    # 4. Drawdown penalty (exponential with smoother curve)
    drawdown_penalty = math.exp(-3 * max_drawdown)  # 低惩罚程度

    # 5. Trade frequency score (prefer 2-5 trades per day)
    trade_frequency_score = math.exp(-((daily_avg_trades - 3.5)**2) / 8)

    # 6. Trade duration score (prefer trades between 2 hours and 2 days)
    optimal_duration = 720  # 12 hours in minutes
    duration_score = math.exp(-((avg_trade_duration - optimal_duration)**2) / (2 * optimal_duration**2))

    # Combine all components with balanced weights
    fitness = (
        profit_score * win_rate_score         # 保持较高权重因为这是主要目标

        # profit_score * 0.30 +           # 保持较高权重因为这是主要目标
        # win_rate_score * 0.15 +         # 略微降低胜率权重
        # risk_adjusted_score * 0.25 +    # 提高风险调整后收益的权重
        # drawdown_penalty * 0.15 +       # 保持适度的回撤惩罚
        # trade_frequency_score * 0.10 +  # 交易频率作为次要因素
        # duration_score * 0.05           # 持续时间作为辅助指标
    )

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
                   f"Final Fitness: {fitness:.4f}")

    # Write to log file
    log_path = os.path.join(LOG_CONFIG['log_dir'], LOG_CONFIG['fitness_log'])
    with open(log_path, 'a') as log_file:
        log_file.write(log_message + '\n')
    
    logger.info(log_message)
    logger.info(f"Log appended to: {log_path}")

    return fitness

def process_results_directory(directory_path: str):
    for filename in os.listdir(directory_path):
        if filename.startswith("backtest_results_") and filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r') as f:
                content = f.read()
            win_rate = extract_win_rate(content)
            print(f"File: {filename}, Win Rate: {win_rate:.2%}")



if __name__ == "__main__":
    # 指定文件路径
    file_path = "/Users/zhangjiawei/Projects/GeneTrader/daily_results/20241207/gen1/results.txt" 
    # 解析回测结果
    parsed_results = parse_backtest_results(file_path)
    
    print("Parsed Results:")
    for key, value in parsed_results.items():
        print(f"{key}: {value}")
    
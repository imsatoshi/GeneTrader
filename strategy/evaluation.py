import sys
import os
from datetime import datetime

# 将项目根目录添加到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

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
        'avg_profit': extract_value(r'│\s*TOTAL\s*│.*?│\s*([\d.-]+)\s*│', default=0),  # Updated pattern
        'total_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*(\d+)\s*/'),
        'daily_avg_trades': extract_value(r'Total/Daily Avg Trades\s*│\s*\d+\s*/\s*([\d.]+)'),
        'avg_trade_duration': parse_duration(extract_value(r'Avg\. Duration Winners\s*│\s*(.*?)\s*│', default='0:00:00', is_string=True))
    }

    return parsed_result

def fitness_function(parsed_result: Dict[str, float]) -> float:
    total_profit_usdt = parsed_result['total_profit_usdt']
    total_profit_percent = parsed_result['total_profit_percent']
    win_rate = parsed_result['win_rate']
    max_drawdown = parsed_result['max_drawdown']
    avg_profit = parsed_result['avg_profit']
    avg_trade_duration = parsed_result['avg_trade_duration']
    total_trades = parsed_result['total_trades']
    sharpe_ratio = parsed_result['sharpe_ratio']

    log_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] total_profit_usdt: {total_profit_usdt}, total_profit_percent: {total_profit_percent}, win_rate: {win_rate}, max_drawdown: {max_drawdown}, avg_profit: {avg_profit}, avg_trade_duration: {avg_trade_duration}, total_trades: {total_trades}, sharpe_ratio: {sharpe_ratio}"
    
    # 定义日志文件路径
    log_filename = "fitness_log.txt"
    log_path = os.path.join(os.path.dirname(__file__), log_filename)
    
    # 将信息追加到日志文件
    with open(log_path, 'a') as log_file:
        log_file.write(log_message + '\n')
    
    logger.info(log_message)
    logger.info(f"Log appended to: {log_path}")

    # 确保至少有一定数量的交易
    if total_trades < 50:
        return float('-inf')

    # 利润因子：总利润与最大回撤的比率
    profit_drawdown_ratio = total_profit_usdt / (max_drawdown + 1e-6)  # 避免除以零

    # 平均交易持续时间因子（假设理想的平均持续时间为4小时）
    duration_factor = min(240 / (avg_trade_duration + 1e-6), 1)

    # 组合这些因素来计算fitness，突出利润
    fitness = (
        total_profit_usdt * 0.5 +          # 总利润的权重增加
        total_profit_percent * 1000 +      # 总利润百分比
        win_rate * 50 +                    # 胜率的权重
        avg_profit * 20 +                  # 平均利润的权重增加
        profit_drawdown_ratio * 0.1 +      # 利润与回撤比率的权重
        duration_factor * 20 +             # 交易持续时间的权重
        sharpe_ratio * 10                  # 加入夏普比率
    )

    return fitness

if __name__ == "__main__":
    import sys

    # 默认文件路径
    default_file = "/Users/zhangjiawei/Downloads/GeneTrader/results/backtest_results_gen1_1725779283_7665.txt"
    
    # 允许从命令行传入文件路径
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file
    
    results = parse_backtest_results(file_path)
    print("Parsed results:")
    for key, value in results.items():
        print(f"{key}: {value}")
    
    fitness = fitness_function(results)
    print(f"\nFitness score: {fitness}")

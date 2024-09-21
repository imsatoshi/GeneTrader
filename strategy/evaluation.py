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

def extract_win_rate(content: str) -> float:
    pattern = r'│\s*TOTAL\s*│.*│\s*(\d+)\s*│.*│.*│.*│.*│\s*\d+\s+\d+\s+\d+\s+([\d.]+)\s*│'
    match = re.search(pattern, content)
    if match:
        total_trades = int(match.group(1))
        win_rate = float(match.group(2)) / 100  # 将百分比转换为小数
        return win_rate
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

    # 添加这行来打印提取的原始胜率值
    print(f"Extracted win rate: {parsed_result['win_rate']}")

    return parsed_result

def fitness_function(parsed_result: Dict[str, Any], generation: int, strategy_name: str) -> float:
    total_profit_usdt = parsed_result['total_profit_usdt']
    total_profit_percent = parsed_result['total_profit_percent']
    win_rate = parsed_result['win_rate']
    max_drawdown = parsed_result['max_drawdown']
    avg_profit = parsed_result['avg_profit']
    avg_trade_duration = parsed_result['avg_trade_duration']
    total_trades = parsed_result['total_trades']
    sharpe_ratio = parsed_result['sharpe_ratio']
    daily_avg_trades = parsed_result['daily_avg_trades']
    profit_drawdown_ratio = total_profit_usdt / (max_drawdown + 1e-6)
    duration_factor = 2 / (1 + math.exp(avg_trade_duration / 1440)) - 1

    def daily_trades_weight(x, mu=0.7, sigma=0.3):
        return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

    daily_trades_factor = daily_trades_weight(daily_avg_trades)

    # 新增：根据win_rate调整权重
    def win_rate_weight(x):
        if x < 0.9:
            return x * 10  # 当胜率低于0.9时，权重较小
        else:
            return 9 + (x - 0.9) * 100  # 当胜率高于0.9时，权重急剧增加

    win_rate_factor = win_rate_weight(win_rate)

    # Calculate individual fitness components
    profit_component = total_profit_percent * 50
    win_rate_component = win_rate_factor
    avg_profit_component = avg_profit * 5
    # profit_drawdown_component = profit_drawdown_ratio * 0.001
    duration_component = duration_factor * 5
    sharpe_component = sharpe_ratio * 0.1
    daily_trades_component = daily_trades_factor * 10

    fitness = (
        profit_component +
        win_rate_component +
        avg_profit_component +
        # profit_drawdown_component +
        duration_component +
        sharpe_component +
        daily_trades_component
    )

    # Update log message to include fitness components and strategy name
    log_message = (f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                   f"Strategy: {strategy_name}, "  # 添加策略名称
                   f"Generation: {generation}, "
                   f"total_profit_usdt: {total_profit_usdt}, "
                   f"total_profit_percent: {total_profit_percent}, "
                   f"win_rate: {win_rate}, "
                   f"max_drawdown: {max_drawdown}, "
                   f"avg_profit: {avg_profit}, "
                   f"avg_trade_duration: {avg_trade_duration}, "
                   f"total_trades: {total_trades}, "
                   f"sharpe_ratio: {sharpe_ratio}, "
                   f"daily_avg_trades: {daily_avg_trades}, "
                   f"profit_component: {profit_component}, "
                   f"win_rate_component: {win_rate_component}, "
                   f"avg_profit_component: {avg_profit_component}, "
                #    f"profit_drawdown_component: {profit_drawdown_component}, "
                   f"duration_component: {duration_component}, "
                   f"sharpe_component: {sharpe_component}, "
                   f"daily_trades_component: {daily_trades_component}, "
                   f"fitness: {fitness}")

    # 定义日志文件路径
    log_filename = "../fitness_log.txt"
    log_path = os.path.join(os.path.dirname(__file__), log_filename)
    
    # 将信息追加到日志文件
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
    file_path = "/Users/zhangjiawei/Projects/GeneTrader/results/backtest_results_gen3_1726875925_4847.txt" 
    # 解析回测结果
    parsed_results = parse_backtest_results(file_path)
    
    print("Parsed Results:")
    for key, value in parsed_results.items():
        print(f"{key}: {value}")
    
    # 假设我们有一个 generation 变量
    generation = 1  # 这个值应该从你的遗传算法主循环中获取

    # 计算适应度
    fitness = fitness_function(parsed_results, generation)
    print(f"\nFitness Score: {fitness}")

    # 额外的验证
    print("\nAdditional Validations:")
    print(f"Win Rate: {parsed_results['win_rate']}")
    print(f"Corrected Win Rate: {min(parsed_results['win_rate'], 1.0)}")
    print(f"Profit/Drawdown Ratio: {parsed_results['total_profit_usdt'] / (parsed_results['max_drawdown'] + 1e-6)}")

    result_dir = "/Users/zhangjiawei/Projects/GeneTrader/results"
    process_results_directory(result_dir)
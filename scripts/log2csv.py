import re
import csv

def parse_line(line):
    # 使用正则表达式提取所需的字段
    pattern = r'Generation: (\d+), total_profit_usdt: ([-\d.]+), total_profit_percent: ([-\d.]+), win_rate: ([-\d.]+), max_drawdown: ([-\d.]+), avg_profit: ([-\d.]+), avg_trade_duration: (\d+), total_trades: ([-\d.]+), sharpe_ratio: ([-\d.]+), daily_avg_trades: ([-\d.]+).*fitness: ([-\d.]+)'
    match = re.search(pattern, line)
    if match:
        return match.groups()
    return None

def convert_log_to_csv(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        
        # 写入CSV头部
        csv_writer.writerow(['Generation', 'total_profit_usdt', 'total_profit_percent', 'win_rate', 'max_drawdown', 
                             'avg_profit', 'avg_trade_duration', 'total_trades', 'sharpe_ratio', 'daily_avg_trades', 'fitness'])
        
        for line in infile:
            data = parse_line(line)
            if data:
                csv_writer.writerow(data)

# 使用函数
input_file = 'fitness_log.txt'  # 请确保这是您的输入文件名
output_file = 'fitness_log.csv'  # 这将是输出的CSV文件名

convert_log_to_csv(input_file, output_file)
print(f"转换完成。输出文件: {output_file}")
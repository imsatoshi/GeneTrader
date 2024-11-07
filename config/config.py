import os

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 日志配置
LOG_CONFIG = {
    'log_dir': os.path.join(PROJECT_ROOT, 'logs'),
    'fitness_log': 'fitness_log.txt',
    'backtest_log': 'backtest_log.txt',
    'diversity_log': 'diversity_log.csv',  # 添加多样性日志配置
    # 可以添加其他日志文件配置
}
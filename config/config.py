import os
from config.settings import settings

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

# 远程服务器配置
REMOTE_SERVER = {
    'hostname': settings.hostname,
    'username': settings.username,
    'key_path': settings.key_path,
    'remote_datadir': '/root/trade/user_data/',  # user_data directory for live or dry-run 
    'remote_strategydir': '/root/trade/user_data/strategies/' #  # strategies directory for live or dry-run 
}


# Bark通知配置
BARK_ENDPOINT = settings.bark_endpoint
BARK_KEY = settings.bark_key
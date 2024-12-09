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
    'api_url': settings.api_url,
    'freqtrade_username': settings.freqtrade_username,
    'freqtrade_password': settings.freqtrade_password,
    'hostname': settings.hostname,
    'username': settings.username,
    'port': settings.port,
    'key_path': settings.key_path,
    'remote_datadir': settings.remote_datadir, 
    'remote_strategydir': settings.remote_strategydir 
}


# Bark通知配置
BARK_ENDPOINT = settings.bark_endpoint
BARK_KEY = settings.bark_key
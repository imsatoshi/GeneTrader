import os
from utils.logging_config import logger

def create_directories(dirs):
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"Created directory: {dir_path}")

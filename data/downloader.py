import os
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

import subprocess
from datetime import date
from typing import List

from config.settings import settings
from utils.logging_config import logger

class DataDownloader:
    def __init__(self):
        self.config_file = settings.config_file
        self.data_dir = settings.data_dir
        self.freqtrade_path = settings.freqtrade_path
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"]

    def download_data(self, start_date: date, end_date: date):
        timerange = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
        
        command = [
            self.freqtrade_path,
            "download-data",
            "--config", self.config_file,
            "--datadir", self.data_dir,
            "--timerange", timerange,
            "-t", *self.timeframes
        ]

        logger.info(f"Downloading data with command: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info("Data download completed successfully")
            logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error downloading data: {e}")
            logger.error(f"Command output: {e.output}")
            raise

def download_data(start_date: date, end_date: date):
    downloader = DataDownloader()
    downloader.download_data(start_date, end_date)

if __name__ == "__main__":
    # For testing purposes
    from datetime import datetime
    start = datetime(2024, 1, 1).date()
    end = date.today()
    download_data(start, end)
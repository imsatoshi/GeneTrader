import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Add timestamp to the log format
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
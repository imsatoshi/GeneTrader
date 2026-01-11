"""Utility for fetching Binance USDT trading pairs with blacklist filtering.

This module provides functions to fetch trading pairs from Binance API,
filter them based on blacklists (manual and delisted coins), and save
the results to configuration files.
"""
import requests
import json
from datetime import datetime
import argparse
import os
from typing import List, Optional, Dict, Any, Set, Tuple, Union
from loguru import logger

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Configuration file path
DELISTED_COINS_FILE = "data/delisted_coins.json"
MANUAL_BLACKLIST: Set[str] = {
    "IDRT",
    "KP3R",
    "OOKI",
    "UNFI",
    "EUR",
    "BNB"
}


def setup_logger() -> None:
    """Set up the logger with file rotation."""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "get_pairs.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB", encoding="utf8")

def load_blacklist() -> Set[str]:
    """Load blacklist including manual blacklist and delisted coins.

    Returns:
        Set of blacklisted coin symbols
    """
    blacklist = MANUAL_BLACKLIST.copy()

    # Load delisted coins
    try:
        delisted_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), DELISTED_COINS_FILE)
        if os.path.exists(delisted_file):
            with open(delisted_file, 'r', encoding='utf-8') as f:
                delisted_data = json.load(f)
                delisted_coins = set(delisted_data.get('delisted_coins', []))

                # Log recently delisted coins
                history = delisted_data.get('delisting_history', [])
                if history:
                    latest_delisted = history[-1]
                    logger.info(f"Recently delisted ({latest_delisted['date']}): {', '.join(latest_delisted['coins'])}")
                    logger.info(f"Delisting notice: {latest_delisted['title']}")

                blacklist.update(delisted_coins)
                logger.info(f"Loaded {len(delisted_coins)} delisted coins from {DELISTED_COINS_FILE}")
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Could not load delisted coins list: {e}")

    logger.info(f"Total blacklisted coins: {len(blacklist)}")
    return blacklist

def get_binance_usdt_pairs(mode: str = 'all', top_n: int = 100) -> Optional[List[str]]:
    """Fetch Binance USDT trading pairs with optional volume filtering.

    Args:
        mode: 'volume' for top N by volume, 'all' for all pairs
        top_n: Number of pairs to return in volume mode

    Returns:
        List of trading pair strings, or None on error
    """
    try:
        # Fetch exchange info
        exchange_info_url = "https://api.binance.com/api/v3/exchangeInfo"
        exchange_info = requests.get(exchange_info_url, timeout=REQUEST_TIMEOUT).json()

        volume_dict: Dict[str, float] = {}
        if mode == 'volume':
            # Fetch 24h volume data
            ticker_url = "https://api.binance.com/api/v3/ticker/24hr"
            ticker_data = requests.get(ticker_url, timeout=REQUEST_TIMEOUT).json()
            volume_dict = {item['symbol']: float(item['quoteVolume']) for item in ticker_data}

        # Get blacklist as a set for O(1) lookup
        blacklist_set = load_blacklist()

        # Filter trading pairs
        usdt_pairs: List[Union[str, Tuple[str, float]]] = []
        skipped_pairs: List[str] = []

        for symbol in exchange_info['symbols']:
            base_asset = symbol['baseAsset']

            # Skip blacklisted coins - O(1) set lookup
            if base_asset in blacklist_set:
                skipped_pairs.append(f"{base_asset}/USDT")
                continue

            # Only get USDT pairs, exclude USD-containing assets
            if (symbol['quoteAsset'] == 'USDT' and
                symbol['status'] == 'TRADING' and
                'USD' not in base_asset):
                pair = f"{base_asset}/USDT"

                if mode == 'volume':
                    quote_volume = volume_dict.get(symbol['symbol'], 0)
                    usdt_pairs.append((pair, quote_volume))
                else:
                    usdt_pairs.append(pair)

        if skipped_pairs:
            logger.info(f"Filtered out pairs: {', '.join(skipped_pairs)}")

        if mode == 'volume':
            # Sort by USDT volume and get top N
            sorted_pairs = sorted(usdt_pairs, key=lambda x: x[1], reverse=True)
            logger.info("Top 10 pairs by USDT volume:")
            for pair, volume in sorted_pairs[:10]:
                logger.info(f"{pair}: {volume:,.2f} USDT")
            return [pair for pair, _ in sorted_pairs[:top_n]]

        return usdt_pairs

    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Data processing error: {e}")
        return None

def save_to_json(data: List[str], filename: Optional[str] = None) -> bool:
    """Save trading pairs data to a JSON file.

    Args:
        data: List of trading pair strings
        filename: Output filename (defaults to timestamped filename)

    Returns:
        True if successful, False otherwise
    """
    if filename is None:
        filename = f"binance_usdt_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Data saved to: {filename}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"Error saving file: {e}")
        return False


def update_config_json(pairs: List[str], output_config: str) -> bool:
    """Update the pair_whitelist in a configuration file.

    Args:
        pairs: List of trading pair strings
        output_config: Output config filename (saved in user_data directory)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read original config as template
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data/config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        config['exchange']['pair_whitelist'] = pairs

        # Save to specified filename in user_data directory
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data', output_config)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully saved trading pairs to: {output_path}")
        return True
    except FileNotFoundError:
        logger.error(f"Config template not found: {config_path}")
        return False
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error updating config file: {e}")
        return False

def main():
    # 设置日志
    setup_logger()
    
    # 添加命令行参数
    parser = argparse.ArgumentParser(description='获取币安USDT交易对')
    parser.add_argument('--mode', type=str, choices=['volume', 'all'], 
                       default='all', help='获取模式：volume-交易量前N个，all-所有交易对')
    parser.add_argument('--top-n', type=int, default=100,
                       help='在 volume 模式下返回的交易对数量（默认：100）')
    parser.add_argument('--output-config', type=str, default='config_new.json',
                       help='输出配置文件的名称 (保存在 user_data 目录下)')
    parser.add_argument('--check-delistings', action='store_true',
                       help='运行前检查最新的下架公告')
    args = parser.parse_args()
    
    # 如果需要，先检查最新的下架公告
    if args.check_delistings:
        logger.info("检查最新下架公告...")
        try:
            from monitor_delistings import main as check_delistings
            check_delistings()
        except Exception as e:
            logger.error(f"检查下架公告时出错: {e}")
    
    # 获取交易对数据
    pairs = get_binance_usdt_pairs(mode=args.mode, top_n=args.top_n)
    
    if pairs:
        # 保存数据到JSON文件
        save_to_json(pairs)
        logger.info(f"共获取到 {len(pairs)} 个USDT交易对")
        
        # 更新配置文件
        update_config_json(pairs, args.output_config)
    else:
        logger.error("获取数据失败")

if __name__ == "__main__":
    main()

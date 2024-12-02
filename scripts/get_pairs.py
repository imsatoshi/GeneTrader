import requests
import json
from datetime import datetime
import argparse
import os
from loguru import logger

# 配置文件路径
DELISTED_COINS_FILE = "data/delisted_coins.json"
MANUAL_BLACKLIST = [
    "IDRT",
    "KP3R",
    "OOKI",
    "UNFI",
    "BNB"
]

def setup_logger():
    """设置日志记录器"""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "get_pairs.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB", encoding="utf8")

def load_blacklist():
    """加载黑名单，包括手动黑名单和已下架币种"""
    # 手动黑名单
    blacklist = set(MANUAL_BLACKLIST)
    
    # 加载已下架币种
    try:
        delisted_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), DELISTED_COINS_FILE)
        if os.path.exists(delisted_file):
            with open(delisted_file, 'r') as f:
                delisted_data = json.load(f)
                delisted_coins = set(delisted_data.get('delisted_coins', []))
                
                # 记录最近下架的币种
                history = delisted_data.get('delisting_history', [])
                if history:
                    latest_delisted = history[-1]
                    logger.info(f"最近下架的币种 ({latest_delisted['date']}): {', '.join(latest_delisted['coins'])}")
                    logger.info(f"下架公告: {latest_delisted['title']}")
                
                blacklist.update(delisted_coins)
                logger.info(f"从 {DELISTED_COINS_FILE} 加载了 {len(delisted_coins)} 个下架币种")
    except Exception as e:
        logger.warning(f"无法加载已下架币种列表: {e}")
    
    logger.info(f"黑名单总计 {len(blacklist)} 个币种")
    return list(blacklist)

def get_binance_usdt_pairs(mode='all', top_n=100):
    """获取币安所有USDT交易对的信息"""
    try:
        # 获取所有交易对信息
        exchange_info_url = "https://api.binance.com/api/v3/exchangeInfo"
        exchange_info = requests.get(exchange_info_url).json()
        
        if mode == 'volume':
            # 获取24小时交易量数据
            ticker_url = "https://api.binance.com/api/v3/ticker/24hr"
            ticker_data = requests.get(ticker_url).json()
            # 使用 quoteVolume (USDT交易量) 作为排序依据
            volume_dict = {item['symbol']: float(item['quoteVolume']) for item in ticker_data}
        
        # 获取黑名单
        blacklists = load_blacklist()
        
        # 过滤交易对
        usdt_pairs = []
        skipped_pairs = []  # 记录被过滤掉的交易对
        
        for symbol in exchange_info['symbols']:
            # 跳过黑名单中的币种
            skip = False
            base_asset = symbol['baseAsset']
            for blacklist in blacklists:
                if blacklist in base_asset:
                    skip = True
                    skipped_pairs.append(f"{base_asset}/USDT")
                    break
            if skip:
                continue
            
            # 只获取USDT交易对，排除包含USD的币种
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
            logger.info(f"已过滤掉以下交易对: {', '.join(skipped_pairs)}")
        
        if mode == 'volume':
            # 按USDT交易金额排序并获取前N个
            sorted_pairs = sorted(usdt_pairs, key=lambda x: x[1], reverse=True)
            logger.info("Top 10 pairs by USDT volume:")
            for pair, volume in sorted_pairs[:10]:
                logger.info(f"{pair}: {volume:,.2f} USDT")
            return [pair for pair, _ in sorted_pairs[:top_n]]
        
        return usdt_pairs
        
    except requests.exceptions.RequestException as e:
        logger.error(f"请求出错: {e}")
        return None
    except Exception as e:
        logger.error(f"处理数据时出错: {e}")
        return None

def save_to_json(data, filename=None):
    """将数据保存为JSON文件"""
    if filename is None:
        # 使用当前时间作为文件名
        filename = f"binance_usdt_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"数据已保存到: {filename}")
        return True
    except Exception as e:
        logger.error(f"保存文件时出错: {e}")
        return False

def update_config_json(pairs, output_config):
    """更新配置文件中的 pair_whitelist"""
    try:
        # 首先读取原始配置文件作为模板
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data/config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['exchange']['pair_whitelist'] = pairs
        
        # 使用指定的文件名保存到 user_data 目录
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data', output_config)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"成功将交易对列表保存到: {output_path}")
        return True
    except Exception as e:
        logger.error(f"更新配置文件时出错: {e}")
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

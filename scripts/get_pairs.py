import requests
import json
from datetime import datetime
import argparse

# 黑名单
blacklists = [
    "IDRT",
    "KP3R",
    "OOKI",
    "UNFI"
]

def get_binance_usdt_pairs(mode='all'):
    """
    获取币安所有USDT交易对的信息
    Args:
        mode (str): 'volume' - 按交易金额返回前100个交易对
                   'all' - 返回所有符合条件的交易对
    """
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
        
        # 过滤交易对
        usdt_pairs = []
        for symbol in exchange_info['symbols']:
            # 跳过黑名单中的币种
            skip = False
            for blacklist in blacklists:
                if blacklist in symbol['symbol']:
                    skip = True
                    break
            if skip:
                continue
            
            # 只获取USDT交易对，排除包含USD的币种
            if (symbol['quoteAsset'] == 'USDT' and 
                symbol['status'] == 'TRADING' and 
                'USD' not in symbol['baseAsset']):
                pair = f"{symbol['baseAsset']}/USDT"
                
                if mode == 'volume':
                    quote_volume = volume_dict.get(symbol['symbol'], 0)
                    usdt_pairs.append((pair, quote_volume))
                else:
                    usdt_pairs.append(pair)
        
        if mode == 'volume':
            # 按USDT交易金额排序并获取前100个
            sorted_pairs = sorted(usdt_pairs, key=lambda x: x[1], reverse=True)
            print("Top 10 pairs by USDT volume:")
            for pair, volume in sorted_pairs[:10]:
                print(f"{pair}: {volume:,.2f} USDT")
            return [pair for pair, _ in sorted_pairs[:100]]
        
        return usdt_pairs
        
    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None
    except Exception as e:
        print(f"处理数据时出错: {e}")
        return None

def save_to_json(data, filename=None):
    """
    将数据保存为JSON文件
    """
    if filename is None:
        # 使用当前时间作为文件名
        filename = f"binance_usdt_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"数据已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存文件时出错: {e}")
        return False

def update_config_json(pairs):
    """
    更新 config.json 文件中的 pair_whitelist
    """
    try:
        with open('user_data/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['exchange']['pair_whitelist'] = pairs
        
        with open('user_data/config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("成功更新 config.json 中的 pair_whitelist")
        return True
    except Exception as e:
        print(f"更新 config.json 时出错: {e}")
        return False

def main():
    # 添加命令行参数
    parser = argparse.ArgumentParser(description='获取币安USDT交易对')
    parser.add_argument('--mode', type=str, choices=['volume', 'all'], 
                       default='all', help='获取模式：volume-交易量前100，all-所有交易对')
    args = parser.parse_args()
    
    # 获取交易对数据
    pairs = get_binance_usdt_pairs(mode=args.mode)
    
    if pairs:
        # 保存数据到JSON文件
        save_to_json(pairs)
        print(f"共获取到 {len(pairs)} 个USDT交易对")
        
        # 更新 config.json
        update_config_json(pairs)
    else:
        print("获取数据失败")

if __name__ == "__main__":
    main()

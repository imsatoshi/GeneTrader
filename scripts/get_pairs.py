import requests
import json
from datetime import datetime

# 黑名单
blacklists = [
    "IDRT",
    "KP3R",
    "OOKI",
    "UNFI"
]

def get_binance_usdt_pairs():
    """
    获取币安所有USDT交易对的信息
    返回简化的交易对列表
    """
    try:
        # 币安API endpoint
        url = "https://api.binance.com/api/v3/exchangeInfo"
        
        # 发送请求
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        
        # 解析响应数据
        data = response.json()
        
        # 过滤出USDT交易对
        usdt_pairs = []
        for symbol in data['symbols']:
            # 只获取状态为交易中的USDT交易对
            for blacklist in blacklists:
                if blacklist in symbol['symbol']:
                    continue

            if symbol['quoteAsset'] == 'USDT' and symbol['status'] == 'TRADING':
                pair = f"{symbol['baseAsset']}/USDT"
                usdt_pairs.append(pair)
        
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
    # 获取交易对数据
    pairs = get_binance_usdt_pairs()
    
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

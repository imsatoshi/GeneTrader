import requests
import json
from datetime import datetime, timedelta
import re
from typing import List, Dict

class BinanceAnnouncementParser:
    def __init__(self):
        self.base_url = "https://www.binance.com/en/support/announcement/c-48"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.binance.com/en/support/announcement/c-48'
        }
        
    def get_announcements(self, days_back: int = 30) -> List[Dict]:
        """获取最近的公告列表"""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            # 使用正则表达式提取页面中的公告数据
            # Binance的页面中通常包含一个JSON数据块
            json_data = re.search(r'window\.APP_STATE\s*=\s*({.*?});', response.text)
            if not json_data:
                print("未能在页面中找到公告数据")
                return []
                
            data = json.loads(json_data.group(1))
            announcements = []
            
            # 解析公告数据
            try:
                articles = data.get('routeProps', {}).get('ce50', {}).get('catalogs', [{}])[0].get('articles', [])
                cutoff_date = datetime.now() - timedelta(days=days_back)
                
                for article in articles:
                    article_date = datetime.fromtimestamp(article.get('releaseDate', 0) / 1000)
                    if article_date >= cutoff_date:
                        announcements.append(article)
                        
            except (KeyError, IndexError) as e:
                print(f"解析公告数据时出错: {e}")
                return []
                
            return announcements
            
        except Exception as e:
            print(f"获取公告时出错: {e}")
            return []
    
    def get_announcement_detail(self, article_id: str) -> Dict:
        """获取公告详情"""
        url = f"https://www.binance.com/en/support/announcement/{article_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # 提取公告内容
            json_data = re.search(r'window\.APP_STATE\s*=\s*({.*?});', response.text)
            if not json_data:
                return {}
                
            data = json.loads(json_data.group(1))
            try:
                article_data = data.get('routeProps', {}).get('c88', {}).get('article', {})
                return {'data': article_data} if article_data else {}
            except (KeyError, IndexError):
                return {}
                
        except Exception as e:
            print(f"获取公告详情时出错: {e}")
            return {}
    
    def find_delisted_coins(self, days_back: int = 30) -> List[str]:
        """查找要下架的币种"""
        delisted_coins = set()
        announcements = self.get_announcements(days_back)
        
        for announcement in announcements:
            title = announcement.get('title', '').upper()
            
            # 检查标题是否包含下架相关关键词
            if any(keyword in title for keyword in ['DELIST', 'DELISTING', 'REMOVAL']):
                detail = self.get_announcement_detail(announcement['id'])
                if not detail.get('data'):
                    continue
                    
                content = detail['data']['content']
                
                # 使用正则表达式查找 "Will Delist XXX" 或类似模式
                # 这里的模式可能需要根据实际公告格式调整
                patterns = [
                    r'(?:will delist|delisting|remove) ([A-Z, ]+)',
                    r'(?:will delist|delisting|remove)[^A-Z]*([A-Z]+(?:, [A-Z]+)*)',
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content.upper())
                    for match in matches:
                        coins = match.group(1).split(',')
                        coins = [coin.strip() for coin in coins if coin.strip()]
                        delisted_coins.update(coins)
        
        return list(delisted_coins)

def update_blacklist(new_coins: List[str]):
    """更新 get_pairs.py 中的黑名单"""
    try:
        with open('scripts/get_pairs.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 找到现有的黑名单
        blacklist_pattern = r'blacklists\s*=\s*\[(.*?)\]'
        match = re.search(blacklist_pattern, content, re.DOTALL)
        
        if not match:
            print("未找到黑名单列表")
            return False
            
        # 解析现有的黑名单
        current_blacklist = []
        for item in re.finditer(r'"([^"]+)"', match.group(1)):
            current_blacklist.append(item.group(1))
            
        # 添加新的币种
        updated_blacklist = sorted(set(current_blacklist) | set(new_coins))
        
        # 格式化新的黑名单
        formatted_blacklist = '[\n    ' + ',\n    '.join(f'"{coin}"' for coin in updated_blacklist) + '\n]'
        
        # 更新文件内容
        new_content = re.sub(blacklist_pattern, f'blacklists = {formatted_blacklist}', content, flags=re.DOTALL)
        
        with open('scripts/get_pairs.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"已添加 {len(set(new_coins) - set(current_blacklist))} 个新的下架币种到黑名单")
        return True
    except Exception as e:
        print(f"更新黑名单时出错: {e}")
        return False

def main():
    parser = BinanceAnnouncementParser()
    print("正在查找最近下架的币种...")
    delisted_coins = parser.find_delisted_coins()
    
    if delisted_coins:
        print(f"找到以下下架币种: {', '.join(delisted_coins)}")
        if update_blacklist(delisted_coins):
            print("成功更新黑名单")
    else:
        print("未找到新的下架币种")

if __name__ == "__main__":
    main()

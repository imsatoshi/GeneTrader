import requests
import sys
import json
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
import os
import re

# Constants
DELISTING_HTML_URL = "https://www.binance.com/en/support/announcement/c-48"
BASE_LINK_URL = "https://www.binance.com"
CODES_FILENAME = "data/processed_announcements.json"
DELISTED_COINS_FILE = "data/delisted_coins.json"

def setup_logger():
    """设置日志记录器"""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "delisting_monitor.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB", encoding="utf8")

def read_processed_announcements():
    """读取已处理的公告记录"""
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), CODES_FILENAME)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading processed announcements: {e}")
        return {}

def write_processed_announcements(data):
    """写入已处理的公告记录"""
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), CODES_FILENAME)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing processed announcements: {e}")

def get_html():
    """获取币安公告页面的HTML"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(DELISTING_HTML_URL, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error fetching HTML: {e}")
        return None

def get_delisting_articles(html):
    """从HTML中提取下架公告"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        script_tag = soup.find("script", {"id": "__APP_DATA"})
        if not script_tag:
            logger.error("Script tag not found")
            return []

        data = json.loads(script_tag.string)
        catalogs = data.get("appState", {}).get("loader", {}).get("dataByRouteId", {}).get("d9b2", {}).get("catalogs", [])
        
        articles = []
        for catalog in catalogs:
            if catalog.get("catalogName") == "Delisting":
                for article in catalog.get("articles", []):
                    code = article.get("code")
                    title = article.get("title")
                    if code and title:
                        link = f"{BASE_LINK_URL}/en/support/announcement/{code}"
                        articles.append({
                            "code": code,
                            "title": title,
                            "link": link,
                            "date": datetime.now().strftime("%Y-%m-%d")
                        })
        return articles
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return []

def extract_delisted_coins(article_content):
    """从公告内容中提取下架的币种"""
    # 常见的下架相关关键词
    delisting_keywords = [
        r"will delist",
        r"delisting",
        r"will remove",
        r"removal of",
    ]
    
    # 如果内容包含这些关键词，尝试提取币种
    content_upper = article_content.upper()
    for keyword in delisting_keywords:
        if re.search(keyword, content_upper, re.IGNORECASE):
            # 排除常见的非币种词
            exclude_words = {
                "THE", "AND", "WILL", "FROM", "SPOT", "TRADING", "PAIRS", "MARGIN",
                "NOTICE", "OF", "ON", "FOR", "IN", "TO", "BE", "IS", "ARE", "WITH",
                "REMOVAL", "DELIST", "DELISTING", "BINANCE", "PERPETUAL", "CONTRACTS",
                "USDT", "BUSD", "ANNOUNCEMENT", "SUSPENSION", "DEPOSITS", "UPDATE",
                "DATE", "FUTURES", "USD"
            }
            
            # 首先尝试查找明确的下架列表模式
            explicit_patterns = [
                r"will delist ([A-Z, ]+) on",
                r"delisting of ([A-Z, ]+)",
                r"will remove ([A-Z, ]+) from",
            ]
            for pattern in explicit_patterns:
                match = re.search(pattern, content_upper, re.IGNORECASE)
                if match:
                    coins = match.group(1).replace(' AND ', ',').split(',')
                    coins = [coin.strip() for coin in coins if coin.strip()]
                    filtered_coins = [coin for coin in coins if coin not in exclude_words]
                    if filtered_coins:
                        return filtered_coins
            
            # 如果没有找到明确的模式，尝试提取所有可能的币种标识符
            coins = re.findall(r'\b[A-Z]{2,10}\b', content_upper)
            filtered_coins = [coin for coin in coins if coin not in exclude_words]
            
            # 如果找到了很多币种，可能是误判，返回空列表
            if len(filtered_coins) > 10:
                return []
                
            return filtered_coins
    return []

def get_announcement_content(article_code):
    """获取公告详细内容"""
    try:
        url = f"{BASE_LINK_URL}/en/support/announcement/{article_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find("script", {"id": "__APP_DATA"})
        if script_tag:
            data = json.loads(script_tag.string)
            article = data.get("appState", {}).get("loader", {}).get("dataByRouteId", {}).get("c88", {}).get("article", {})
            return article.get("content", "")
    except Exception as e:
        logger.error(f"Error fetching announcement content: {e}")
    return ""

def update_delisted_coins(new_coins, article_info):
    """更新已下架币种列表"""
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), DELISTED_COINS_FILE)
        
        # 读取现有数据或创建新的数据结构
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
        else:
            data = {
                "delisted_coins": [],
                "delisting_history": []
            }
        
        # 更新币种列表
        existing_coins = set(data.get("delisted_coins", []))
        new_coins_set = set(new_coins)
        
        if new_coins_set - existing_coins:  # 如果有新的币种
            # 更新主列表
            data["delisted_coins"] = sorted(list(existing_coins | new_coins_set))
            
            # 添加历史记录
            history_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "coins": sorted(list(new_coins_set - existing_coins)),
                "source": article_info["link"],
                "title": article_info["title"]
            }
            
            # 确保 delisting_history 存在
            if "delisting_history" not in data:
                data["delisting_history"] = []
            
            data["delisting_history"].append(history_entry)
            
            # 写入文件
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Added new delisted coins: {new_coins_set - existing_coins}")
            return True
    except Exception as e:
        logger.error(f"Error updating delisted coins: {e}")
    return False

def main():
    setup_logger()
    logger.info("Starting delisting monitor...")
    
    # 读取已处理的公告
    processed_announcements = read_processed_announcements()
    
    # 获取最新公告
    html = get_html()
    if not html:
        return
    
    articles = get_delisting_articles(html)
    if not articles:
        logger.info("No delisting announcements found")
        return
    
    # 处理新公告
    for article in articles:
        if article["code"] not in processed_announcements:
            logger.info(f"Processing new announcement: {article['title']}")
            
            # 直接从标题中提取下架币种
            delisted_coins = extract_delisted_coins(article['title'])
            if delisted_coins:
                logger.info(f"Found delisted coins in announcement: {delisted_coins}")
                # 更新下架币种列表
                if update_delisted_coins(delisted_coins, article):
                    # 记录已处理的公告
                    processed_announcements[article["code"]] = {
                        "date": article["date"],
                        "title": article["title"],
                        "coins": delisted_coins
                    }
                    write_processed_announcements(processed_announcements)
            else:
                logger.info("No delisted coins found in the announcement")

if __name__ == '__main__':
    main()

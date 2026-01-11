"""Binance delisting announcement monitor.

This module monitors Binance announcement pages for cryptocurrency delisting
notices and maintains a list of delisted coins for use in trading pair filtering.
"""
import requests
import sys
import json
from bs4 import BeautifulSoup
from loguru import logger
from datetime import datetime
import os
import re
from typing import Dict, List, Any, Optional, Set

# Constants
DELISTING_HTML_URL = "https://www.binance.com/en/support/announcement/c-48"
BASE_LINK_URL = "https://www.binance.com"
CODES_FILENAME = "data/processed_announcements.json"
DELISTED_COINS_FILE = "data/delisted_coins.json"
REQUEST_TIMEOUT = 30  # seconds


def setup_logger() -> None:
    """Set up the logger with file rotation."""
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "delisting_monitor.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(log_file, rotation="10 MB", encoding="utf8")


def read_processed_announcements() -> Dict[str, Any]:
    """Read previously processed announcements from disk.

    Returns:
        Dictionary mapping announcement codes to their processing data
    """
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), CODES_FILENAME)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading processed announcements: {e}")
        return {}


def write_processed_announcements(data: Dict[str, Any]) -> bool:
    """Write processed announcements to disk.

    Args:
        data: Dictionary of processed announcements

    Returns:
        True if successful, False otherwise
    """
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), CODES_FILENAME)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except IOError as e:
        logger.error(f"Error writing processed announcements: {e}")
        return False

def get_html() -> Optional[str]:
    """Fetch the Binance announcement page HTML.

    Returns:
        HTML content as string, or None on error
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        response = requests.get(DELISTING_HTML_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching HTML: {e}")
        return None


def get_delisting_articles(html: str) -> List[Dict[str, str]]:
    """Extract delisting announcements from the HTML page.

    Args:
        html: Raw HTML content from Binance announcements page

    Returns:
        List of article dictionaries with code, title, link, and date fields
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        script_tag = soup.find("script", {"id": "__APP_DATA"})
        if not script_tag:
            logger.error("Script tag not found")
            return []

        data = json.loads(script_tag.string)
        catalogs = data.get("appState", {}).get("loader", {}).get("dataByRouteId", {}).get("d9b2", {}).get("catalogs", [])

        articles: List[Dict[str, str]] = []
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
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing HTML: {e}")
        return []

def extract_delisted_coins(article_content: str) -> List[str]:
    """Extract delisted coin symbols from announcement content.

    Uses keyword matching and regex patterns to identify cryptocurrency
    symbols mentioned in delisting announcements.

    Args:
        article_content: Text content of the announcement (title or body)

    Returns:
        List of uppercase coin symbols found in the content
    """
    # Common delisting-related keywords
    delisting_keywords = [
        r"will delist",
        r"delisting",
        r"will remove",
        r"removal of",
    ]

    content_upper = article_content.upper()

    for keyword in delisting_keywords:
        if re.search(keyword, content_upper, re.IGNORECASE):
            # Words to exclude (common non-coin terms)
            exclude_words: Set[str] = {
                "THE", "AND", "WILL", "FROM", "SPOT", "TRADING", "PAIRS", "MARGIN",
                "NOTICE", "OF", "ON", "FOR", "IN", "TO", "BE", "IS", "ARE", "WITH",
                "REMOVAL", "DELIST", "DELISTING", "BINANCE", "PERPETUAL", "CONTRACTS",
                "USDT", "BUSD", "ANNOUNCEMENT", "SUSPENSION", "DEPOSITS", "UPDATE",
                "DATE", "FUTURES", "USD"
            }

            # Try explicit delisting list patterns first
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

            # Fall back to extracting all potential coin identifiers
            coins = re.findall(r'\b[A-Z]{2,10}\b', content_upper)
            filtered_coins = [coin for coin in coins if coin not in exclude_words]

            # Too many matches likely indicates false positive
            if len(filtered_coins) > 10:
                return []

            return filtered_coins
    return []

def get_announcement_content(article_code: str) -> str:
    """Fetch the detailed content of a specific announcement.

    Args:
        article_code: Unique identifier for the announcement

    Returns:
        HTML content of the announcement body, or empty string on error
    """
    try:
        url = f"{BASE_LINK_URL}/en/support/announcement/{article_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find("script", {"id": "__APP_DATA"})
        if script_tag:
            data = json.loads(script_tag.string)
            article = data.get("appState", {}).get("loader", {}).get("dataByRouteId", {}).get("c88", {}).get("article", {})
            return article.get("content", "")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching announcement content: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing announcement content: {e}")
    return ""


def update_delisted_coins(new_coins: List[str], article_info: Dict[str, str]) -> bool:
    """Update the delisted coins database with newly discovered coins.

    Args:
        new_coins: List of newly discovered delisted coin symbols
        article_info: Dictionary with link and title of the source announcement

    Returns:
        True if new coins were added, False otherwise
    """
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), DELISTED_COINS_FILE)

        # Load existing data or create new structure
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "delisted_coins": [],
                "delisting_history": []
            }

        existing_coins = set(data.get("delisted_coins", []))
        new_coins_set = set(new_coins)

        if new_coins_set - existing_coins:  # If there are new coins
            # Update main list
            data["delisted_coins"] = sorted(list(existing_coins | new_coins_set))

            # Add history entry
            history_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "coins": sorted(list(new_coins_set - existing_coins)),
                "source": article_info["link"],
                "title": article_info["title"]
            }

            if "delisting_history" not in data:
                data["delisting_history"] = []

            data["delisting_history"].append(history_entry)

            # Write to file
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Added new delisted coins: {new_coins_set - existing_coins}")
            return True
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error updating delisted coins: {e}")
    return False

def main() -> None:
    """Main entry point for the delisting monitor.

    Fetches the latest announcements from Binance, extracts delisted coins,
    and updates the local database of delisted coins.
    """
    setup_logger()
    logger.info("Starting delisting monitor...")

    # Load previously processed announcements
    processed_announcements = read_processed_announcements()

    # Fetch latest announcements
    html = get_html()
    if not html:
        logger.error("Failed to fetch announcement page")
        return

    articles = get_delisting_articles(html)
    if not articles:
        logger.info("No delisting announcements found")
        return

    # Process new announcements
    new_count = 0
    for article in articles:
        if article["code"] not in processed_announcements:
            logger.info(f"Processing new announcement: {article['title']}")

            # Extract delisted coins from the title
            delisted_coins = extract_delisted_coins(article['title'])
            if delisted_coins:
                logger.info(f"Found delisted coins: {delisted_coins}")
                if update_delisted_coins(delisted_coins, article):
                    processed_announcements[article["code"]] = {
                        "date": article["date"],
                        "title": article["title"],
                        "coins": delisted_coins
                    }
                    write_processed_announcements(processed_announcements)
                    new_count += 1
            else:
                logger.info("No delisted coins found in the announcement")

    logger.info(f"Processed {new_count} new delisting announcements")


if __name__ == '__main__':
    main()

"""Freqtrade API restart utility.

This module provides functions for restarting a Freqtrade instance via its API.
Credentials should be set via environment variables for security.
"""
import os
import requests
from requests.auth import HTTPBasicAuth
import logging
from typing import Optional

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def test_ping(api_url: str) -> bool:
    """Test API connectivity.

    Args:
        api_url: The base URL of the Freqtrade API

    Returns:
        True if ping successful, False otherwise
    """
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        logger.info(f"Ping successful: {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Ping failed: {e}")
        return False


def get_access_token(api_url: str, username: Optional[str] = None,
                     password: Optional[str] = None) -> str:
    """Get access token from Freqtrade API.

    Credentials are read from environment variables if not provided:
    - FREQTRADE_USERNAME
    - FREQTRADE_PASSWORD

    Args:
        api_url: The base URL of the Freqtrade API
        username: API username (optional, uses env var if not provided)
        password: API password (optional, uses env var if not provided)

    Returns:
        Access token string

    Raises:
        ValueError: If credentials are not provided or found in environment
        requests.exceptions.RequestException: If API request fails
    """
    username = username or os.environ.get('FREQTRADE_USERNAME')
    password = password or os.environ.get('FREQTRADE_PASSWORD')

    if not username or not password:
        raise ValueError(
            "Credentials not provided. Set FREQTRADE_USERNAME and FREQTRADE_PASSWORD "
            "environment variables, or pass username/password parameters."
        )

    response = requests.post(
        f"{api_url}/api/v1/token/login",
        data={"username": username, "password": password},
        timeout=30
    )
    response.raise_for_status()
    return response.json()['access_token']


def restart_freqtrade(api_url: str, access_token: str) -> bool:
    """Restart Freqtrade by reloading its configuration.

    Args:
        api_url: The base URL of the Freqtrade API
        access_token: Valid access token for authentication

    Returns:
        True if restart successful, False otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.post(
            f"{api_url}/api/v1/reload_config",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        logger.info("Freqtrade restarted successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to restart Freqtrade: {e}")
        return False


if __name__ == "__main__":
    # API URL from environment variable
    api_url = os.environ.get('FREQTRADE_API_URL')

    if not api_url:
        print("Error: FREQTRADE_API_URL environment variable not set.")
        print("Usage: Set the following environment variables before running:")
        print("  export FREQTRADE_API_URL='https://your-api-url.com'")
        print("  export FREQTRADE_USERNAME='your_username'")
        print("  export FREQTRADE_PASSWORD='your_password'")
        exit(1)

    try:
        access_token = get_access_token(api_url)
        success = restart_freqtrade(api_url, access_token)
        if success:
            print("Freqtrade restart was successful.")
        else:
            print("Freqtrade restart failed.")
            exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        exit(1)

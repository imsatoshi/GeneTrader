import requests
from requests.auth import HTTPBasicAuth
import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def test_ping(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        print("Ping successful:", response.text)
    except requests.exceptions.RequestException as e:
        print("Ping failed:", e)

def get_access_token(api_url):
    response = requests.post(f"{api_url}/api/v1/token/login", data={"username": "jwzhang", "password": "zhangjiawei"})
    response.raise_for_status()
    return response.json()['access_token']


def restart_freqtrade(api_url, access_token):
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.post(
            f"{api_url}/api/v1/reload_config",
            headers=headers
        )
        response.raise_for_status()
        logger.info("Freqtrade restarted successfully.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to restart Freqtrade: {e}")
        return False

if __name__ == "__main__":
    # Replace these with your actual API URL and access token
    # api_url = "http://192.168.71.47:8888"
    api_url = "https://xxxs.xxx.cloud"

    access_token = get_access_token(api_url)    
    # Call the function and print the result
    success = restart_freqtrade(api_url, access_token)
    if success:
        print("Freqtrade restart was successful.")
    else:
        print("Freqtrade restart failed.")

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



def restart_freqtrade(api_url, access_token):
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.post(
            f"{api_url}/v1/restart",
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
    api_url = "https://dailybuy.jwzhang.cloud"
    access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZGVudGl0eSI6eyJ1Ijoiand6In0sImV4cCI6MTczMzU1NzYyNiwiaWF0IjoxNzMzNTU2NzI2LCJ0eXBlIjoiYWNjZXNzIn0.HI5nhy0AL0v6DR7dxWNaozX1Vdm67FeGD4eRWjPzUBQ"

    # Call the function and print the result
    success = restart_freqtrade(api_url, access_token)
    if success:
        print("Freqtrade restart was successful.")
    else:
        print("Freqtrade restart failed.")


    # 这里是你的 API URL
    api_url = "https://dailybuy.jwzhang.cloud"
    
    # 调用测试函数
    test_ping(api_url)
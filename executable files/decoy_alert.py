import requests
import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# Your unique Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Your personal Chat ID
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    """Sends a text alert to your phone via Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Success! Check your Telegram app.")
        else:
            print(f"❌ Failed to send. Error: {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    send_telegram_alert("🚨 TEST ALERT: Cyber-Physical Decoy System is Online.")
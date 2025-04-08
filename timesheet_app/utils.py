import requests
import os
from dotenv import load_dotenv

load_dotenv()

def send_telegram_message(chat_id, message, file=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

    if file:
        # Send a file with the message
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        files = {"document": (file.name, file, file.content_type)}  # Send file directly
        data = {"chat_id": chat_id, "caption": message, "parse_mode": "HTML"}
        response = requests.post(url, data=data, files=files)
    else:
        # Send a text message
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload)

    return response.json()

import requests

def send_telegram_message(chat_id, message):
    bot_token = '7673248883:AAF7-QGDEBwZG0IVqrXAGdZ92s0no80adFA'  # Replace with your bot token
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    return response.json()

import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NETWORK_TIMEOUT

# We track the last message ID so the bot doesn't read old 'Y's from yesterday
LAST_UPDATE_ID = None

def send_telegram_message(message):
    """Sends a formatted HTML message to the configured Telegram chat."""
    if TELEGRAM_BOT_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN_HERE':
        print("⚠️ Telegram Token not configured. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=NETWORK_TIMEOUT)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Failed to send Telegram message: {e}")

def wait_for_telegram_approval():
    """Polls the Telegram API waiting for the user to reply 'Y' or 'N'."""
    global LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    # Step 1: Clear the queue so we don't accidentally read old messages
    try:
        resp = requests.get(url, timeout=NETWORK_TIMEOUT).json()
        if resp.get('ok') and len(resp['result']) > 0:
            LAST_UPDATE_ID = resp['result'][-1]['update_id']
    except Exception:
        pass

    # Step 2: Ask the user
    print("⏳ Waiting for your reply on Telegram...")
    send_telegram_message("⏸️ <b>Waiting for approval.</b>\nReply with <b>Y</b> to proceed to the next year, or <b>N</b> to stop.")

    # Step 3: Listen for the answer
    while True:
        params = {'offset': LAST_UPDATE_ID + 1} if LAST_UPDATE_ID else {}
        try:
            response = requests.get(url, params=params, timeout=NETWORK_TIMEOUT)
            data = response.json()

            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    LAST_UPDATE_ID = update['update_id']
                    
                    # Ensure the message is text and from the correct chat
                    if 'message' in update and 'text' in update['message']:
                        chat_id = str(update['message']['chat']['id'])
                        
                        if chat_id == TELEGRAM_CHAT_ID:
                            text = update['message']['text'].strip().lower()
                            
                            if text == 'y':
                                send_telegram_message("▶️ <b>Proceeding to the next year...</b>")
                                return True
                            elif text == 'n':
                                send_telegram_message("🛑 <b>Pipeline stopped by user.</b>")
                                return False
                            else:
                                send_telegram_message("⚠️ Unrecognized command. Please reply with exactly <b>Y</b> or <b>N</b>.")
        except Exception as e:
            print(f"Polling error: {e}")

        # Sleep for 3 seconds before asking Telegram again (prevents rate-limiting)
        time.sleep(3)
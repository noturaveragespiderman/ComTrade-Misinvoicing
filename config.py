import csv
import os

# ==========================================
# 1. CREDENTIALS (PASTE YOUR KEYS HERE)
# ==========================================
# Get your API key: https://comtradedeveloper.un.org/
COMTRADE_API_KEY = 'PASTE_YOUR_UN_COMTRADE_KEY_HERE'

# Get your Bot Token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN = 'PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE'

# Get your Chat ID from @userinfobot on Telegram
TELEGRAM_CHAT_ID = 'PASTE_YOUR_TELEGRAM_CHAT_ID_HERE'

# ==========================================
# 2. SAFETY CHECK (Do not change)
# ==========================================
if 'PASTE_YOUR' in COMTRADE_API_KEY or 'PASTE_YOUR' in TELEGRAM_BOT_TOKEN:
    print("\n" + "!"*50)
    print("⚠️  SETUP ERROR: API KEYS MISSING")
    print("!"*50)
    print("Please open 'config.py' in a text editor and paste")
    print("your keys into the first section.")
    print("!"*50 + "\n")
    exit(1)

# ==========================================
# 3. PIPELINE SETTINGS
# ==========================================
NETWORK_TIMEOUT = 10  
SLEEP_TIMEOUT = 5     
DIRECTORY = './comtrade_raw_data'

# Ensure the download folder exists
if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)

# ==========================================
# 4. DYNAMIC TARGETS (Read from CSV)
# ==========================================
targets = {}
try:
    with open('targets.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) 
        for row in reader:
            if len(row) == 2:
                targets[row[0].strip()] = row[1].strip()
except FileNotFoundError:
    print("Error: 'targets.csv' not found. Please ensure it is in the same folder.")
    exit(1)

YEARS = [y.strip() for y in targets.get('Years', '').split(',')]
COUNTRY_CODES = targets.get('Countries', '').replace(' ', '')
HS_CODES = targets.get('HSCodes', '').replace(' ', '')
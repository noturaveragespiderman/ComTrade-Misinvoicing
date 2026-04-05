import csv
import os
from dotenv import load_dotenv

# Load the hidden .env file
load_dotenv()

# ==========================================
# 1. CREDENTIALS (Securely loaded!)
# ==========================================
COMTRADE_API_KEY = os.getenv('COMTRADE_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ==========================================
# 2. PIPELINE TIMEOUTS & SETTINGS
# ==========================================
NETWORK_TIMEOUT = 10  
SLEEP_TIMEOUT = 5     
DIRECTORY = './comtrade_raw_data'

# ==========================================
# 3. DYNAMIC TARGETS (Read from CSV)
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
    print("Error: 'targets.csv' not found. Please create it.")
    exit(1)

YEARS = [y.strip() for y in targets.get('Years', '').split(',')]
COUNTRY_CODES = targets.get('Countries', '').replace(' ', '')
HS_CODES = targets.get('HSCodes', '').replace(' ', '')
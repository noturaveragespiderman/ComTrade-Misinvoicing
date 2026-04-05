# UN Comtrade Trade Data Pipeline

A Python pipeline that downloads, filters, and saves bilateral trade data from the [UN Comtrade API](https://comtradedeveloper.un.org/), with Telegram notifications and interactive approval between years.

---

## How It Works

1. Reads target years, country codes, and HS chapters from `targets.csv`
2. For each year, queries the Comtrade API for an expected row count, then bulk-downloads the raw data files
3. Filters each file by HS chapter and trade flow (imports/exports and re-imports/re-exports)
4. Saves a cleaned CSV per year to `./comtrade_raw_data/`
5. Sends a Telegram notification after each year with a summary and data sample
6. Pauses and waits for you to reply **Y** (continue) or **N** (stop) on Telegram before moving to the next year

---

## Project Structure

```
.
├── main.py           # Pipeline logic and entry point
├── config.py         # API keys, settings, and target loading
├── notifier.py       # Telegram send/receive helpers
├── targets.csv       # Your query parameters (years, countries, HS codes)
└── requirements.txt  # Python dependencies
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get your API keys

| Key | Where to get it |
|---|---|
| `COMTRADE_API_KEY` | [comtradedeveloper.un.org](https://comtradedeveloper.un.org/) |
| `TELEGRAM_BOT_TOKEN` | Message **@BotFather** on Telegram → `/newbot` |
| `TELEGRAM_CHAT_ID` | Message **@userinfobot** on Telegram |

### 3. Paste your keys into `config.py`

```python
COMTRADE_API_KEY   = 'your-key-here'
TELEGRAM_BOT_TOKEN = 'your-bot-token-here'
TELEGRAM_CHAT_ID   = 'your-chat-id-here'
```

The script will exit immediately with a clear error if any key is still set to its placeholder value.

### 4. Configure your targets in `targets.csv`

```csv
Parameter,Value
Years,"2015,2016,2017"
Countries,"12,24,72,108"
HSCodes,"25,26,27,44"
```

| Field | Description |
|---|---|
| `Years` | Comma-separated list of years to download |
| `Countries` | Comma-separated UN reporter country codes |
| `HSCodes` | Comma-separated 2-digit HS chapters to keep |

> Country codes follow the UN M49 standard. A full list is available on the [UN Comtrade portal](https://comtrade.un.org/data/cache/reporterAreas.json).

---

## Running the Pipeline

```bash
python main.py
```

The pipeline will print progress to the console and send live updates to your Telegram chat. After each year completes, reply **Y** or **N** in Telegram to continue or stop.

---

## Output

Cleaned files are saved to `./comtrade_raw_data/` as `cleaned_data_{year}.csv`. Key columns include:

| Column | Description |
|---|---|
| `reportercode` | UN code of the reporting country |
| `partnercode` | UN code of the trade partner |
| `cmdcode_clean` | HS commodity code (trailing `.0` stripped) |
| `flowcode_clean` | Trade flow: `M` (import), `X` (export), `RM`, `RX` (re-import/re-export) |
| `primaryvalue` | Trade value in USD |

Raw `.txt` and `.gz` files are deleted after processing. To inspect the raw files, comment out the `os.remove(file)` line in `main.py`.

---

## Configuration Reference (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `NETWORK_TIMEOUT` | `10` | Seconds before a network request times out |
| `SLEEP_TIMEOUT` | `5` | General sleep between operations |
| `DIRECTORY` | `./comtrade_raw_data` | Output folder for cleaned CSVs |

---

## Notes

- The Comtrade bulk download API requires a **paid subscription key**. The free tier does not support bulk downloads.
- Country reporters are queried in batches of 3 to avoid URL length limits on the count endpoint.
- The pipeline respects UN API rate limits with a 2-second sleep between count batches.
- An SSL verification bypass (`ssl._create_unverified_context`) is applied globally in `main.py` to handle certain network environments. Remove it if your environment does not require it.

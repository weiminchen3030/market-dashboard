import subprocess
import sys
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import logging
import re
import os

from data_fetcher import get_stock_data

logging.basicConfig(level=logging.WARNING)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


# ── Simple scrapers ─────────────────────────────────────────────────────────────

def get_crypto_fng():
    try:
        res = requests.get('https://api.alternative.me/fng/?limit=1', timeout=10)
        d = res.json()['data'][0]
        return f"{d['value']} ({d['value_classification']})"
    except Exception as e:
        logging.error(f"Crypto FnG Error: {e}")
        return "N/A"


def get_naaim():
    try:
        res = requests.get("https://naaim.org/programs/naaim-exposure-index/",
                            headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        tables = soup.find_all('table')
        if tables:
            rows = tables[0].find_all('tr')
            if len(rows) > 1:
                cols = [c.text.strip() for c in rows[1].find_all(['th', 'td'])]
                return {"date": cols[0], "value": cols[1]}
        return {"date": "N/A", "value": "N/A"}
    except Exception as e:
        logging.error(f"NAAIM Error: {e}")
        return {"date": "N/A", "value": "N/A"}


def get_vix_data():
    """Fetch VIX and VVIX directly from TradingView using requests and regex."""
    try:
        def fetch_tv_price(tv_sym):
            r = requests.get(f"https://www.tradingview.com/symbols/{tv_sym}/", headers=HEADERS, timeout=10)
            m = re.search(r'\"price\":\s*([\d\.]+)', r.text)
            return float(m.group(1)) if m else None
            
        v = fetch_tv_price("CBOE-VIX")
        vv = fetch_tv_price("CBOE-VVIX")
        
        if v is not None and vv is not None:
            return {"VIX": round(v, 2), "VVIX": round(vv, 2), "VIX/VVIX": round(v / vv, 4)}
        return {"VIX": "N/A", "VVIX": "N/A", "VIX/VVIX": "N/A"}
    except Exception as e:
        logging.error(f"VIX Error: {e}")
        return {"VIX": "N/A", "VVIX": "N/A", "VIX/VVIX": "N/A"}


# ── NYMO via CBOE/Yahoo option ─────────────────────────────────────────────────
def get_nymo():
    """Fetch latest $NYMO value from StockCharts public chart data."""
    try:
        # StockCharts exposes ticker data via this endpoint
        url = "https://stockcharts.com/c-sc/sc?s=$NYMO&p=D&b=5&g=0&i=0&a=&r=1"
        # We can only get a chart image from stockcharts free.
        # Fallback: use the Barchart API (they offer an NYMO ticker)
        res = requests.get(
            "https://www.barchart.com/stocks/quotes/$NYMO/overview",
            headers=HEADERS, timeout=10
        )
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Last price is in meta og:description or a specific div
            m = re.search(r'\$NYMO.*?([-+]?\d+\.\d{2})', res.text, re.IGNORECASE)
            if m:
                return m.group(1)
        return "N/A"
    except Exception as e:
        logging.error(f"NYMO Error: {e}")

def get_aaii_from_playwright():
    """Run playwright_worker with extra AAII scraping target."""
    worker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playwright_worker.py")
    try:
        result = subprocess.run(
            [sys.executable, worker],
            capture_output=True, text=True, timeout=120
        )
        data = json.loads(result.stdout.strip())
        return data.get("AAII", {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"})
    except:
        return {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"}


# ── TD Sequential (Tom DeMark 神奇九轉) ────────────────────────────────────────

def calculate_td_setup(df: pd.DataFrame) -> pd.DataFrame:
    """
    TD Setup (神奇九轉) rules:
    - Each close HIGHER than close 4 bars ago → High (sell) counter +1
    - Each close LOWER  than close 4 bars ago → Low  (buy)  counter +1
    - Counter increments INDEFINITELY as long as direction holds.
    - Resets to 0 ONLY when direction reverses.
    - 9 and 13 are milestone markers (arrows); numbers continue past them.
    """
    closes = df['Close']
    n = len(closes)
    td_up   = [0] * n  # sell setup (High): above close 4 bars ago
    td_down = [0] * n  # buy  setup (Low):  below close 4 bars ago

    for i in range(4, n):
        if closes.iloc[i] > closes.iloc[i - 4]:
            # Count goes 1, 2, 3 … indefinitely; resets only when direction reverses
            td_up[i]   = td_up[i - 1] + 1 if td_up[i - 1] > 0 else 1
            td_down[i] = 0
        elif closes.iloc[i] < closes.iloc[i - 4]:
            td_down[i] = td_down[i - 1] + 1 if td_down[i - 1] > 0 else 1
            td_up[i]   = 0
        # equal → both stay 0

    df = df.copy()
    df['TD_Up']   = td_up
    df['TD_Down'] = td_down
    df['MA20']    = closes.rolling(20).mean()
    df['MA60']    = closes.rolling(60).mean()
    df['MA120']   = closes.rolling(120).mean()

    # Keep only weekdays
    df = df[df.index.dayofweek < 5]

    latest_up   = df['TD_Up'].iloc[-1]
    latest_down = df['TD_Down'].iloc[-1]
    if latest_up > 0:
        label = f"High {int(latest_up)}"
    elif latest_down > 0:
        label = f"Low {int(latest_down)}"
    else:
        label = "Neutral"

    return df, label


def get_td_sequential():
    symbols = ['SPY', 'QQQ', 'DIA', 'IWM', '^VIX']
    results = {}
    for sym in symbols:
        try:
            hist = get_stock_data(sym, period="1y")
            hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
            hist = hist[hist.index.dayofweek < 5]
            if len(hist) > 13:
                df, label = calculate_td_setup(hist)
                current_price = round(hist['Close'].iloc[-1], 2)
                last_close = round(hist['Close'].iloc[-2], 2) if len(hist) > 1 else current_price
                
                results[sym] = {
                    "Current Price": current_price,
                    "Last Close": last_close,
                    "TD": label, "DF": df
                }
            else:
                results[sym] = {"Current Price": "N/A", "Last Close": "N/A", "TD": "N/A", "DF": None}
        except Exception as e:
            logging.error(f"TD Error {sym}: {e}")
            results[sym] = {"Current Price": "N/A", "Last Close": "N/A", "TD": "N/A", "DF": None}
    return results


# ── Playwright via subprocess ───────────────────────────────────────────────────
def scrape_with_playwright():
    default = {"TradingLogic": "N/A", "CNNFearGreed": "N/A", "Truflation": "N/A",
               "AAII": {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"}}
    worker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playwright_worker.py")
    try:
        result = subprocess.run(
            [sys.executable, worker],
            capture_output=True, text=True, timeout=120
        )
        stdout = result.stdout.strip()
        if stdout:
            return json.loads(stdout)
        logging.error(f"PW worker stderr: {result.stderr[-500:]}")
        return default
    except Exception as e:
        logging.error(f"Subprocess error: {e}")
        return default


if __name__ == "__main__":
    print("Crypto FnG  :", get_crypto_fng())
    print("NAAIM       :", get_naaim())
    print("VIX data    :", get_vix_data())
    print("NYMO        :", get_nymo())

    liq = get_us_liquidity()
    print("US Liquidity:", liq['value'], liq['delta'], "as of", liq['date'])
    if liq['df'] is not None:
        print("  DF tail:\n", liq['df'].tail(3))

    td = get_td_sequential()
    for sym, d in td.items():
        df_len = len(d["DF"]) if d["DF"] is not None else 0
        print(f"  {sym}: price={d['Price']}  TD={d['TD']}  rows={df_len}")

    print("Playwright  :", scrape_with_playwright())

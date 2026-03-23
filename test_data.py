import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import logging

logging.basicConfig(level=logging.INFO)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def test_trading_logic():
    print("Testing Trading Logic...")
    try:
        res = requests.get('https://www.trading-logic.com/en', headers=headers, timeout=10)
        print("Status:", res.status_code)
        # We need to find "breadth"
        if "breadth" in res.text.lower():
            print("Found 'breadth' in text")
        else:
            print("Did NOT find 'breadth'")
    except Exception as e:
        print("Error:", e)
        
def test_naaim():
    print("Testing NAAIM...")
    try:
        res = requests.get('https://naaim.org/programs/naaim-exposure-index/', headers=headers, timeout=10)
        print("Status:", res.status_code)
    except Exception as e:
        print("Error:", e)

def test_aaii():
    print("Testing AAII...")
    try:
        res = requests.get('https://www.aaii.com/sentimentsurvey', headers=headers, timeout=10)
        print("Status:", res.status_code)
    except Exception as e:
        print("Error:", e)

def test_crypto_fng():
    print("Testing Crypto FnG...")
    try:
        res = requests.get('https://api.alternative.me/fng/?limit=1', timeout=10)
        print("Status:", res.status_code)
        print("Data:", res.json())
    except Exception as e:
        print("Error:", e)

def test_yfinance():
    print("Testing yfinance for symbols...")
    symbols = ['^NYMO', '^VIX', '^VVIX', 'SPY', 'QQQ', 'DIA', 'IWM']
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d")
            if not hist.empty:
                print(f"{sym}: OK, Got {len(hist)} days of data")
            else:
                print(f"{sym}: Empty data")
        except Exception as e:
            print(f"{sym} Error:", e)

if __name__ == "__main__":
    test_trading_logic()
    test_naaim()
    test_aaii()
    test_crypto_fng()
    test_yfinance()

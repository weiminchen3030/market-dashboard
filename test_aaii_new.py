import requests
from bs4 import BeautifulSoup
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

print("=== Testing sentiment.aaii.com ===")
try:
    r = requests.get('https://sentiment.aaii.com/', headers=HEADERS, timeout=10)
    print("Status:", r.status_code)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        print("Page title:", soup.title.string if soup.title else "No title")
        # Just print first 500 chars of body text
        print(soup.body.text[:500].strip() if soup.body else "No body text")
except Exception as e:
    print("Error:", e)

print("\n=== Testing TradingView AAII-BULLISH ===")
try:
    r = requests.get('https://www.tradingview.com/symbols/AAII-BULLISH/', headers=HEADERS, timeout=10)
    print("Status:", r.status_code)
    if r.status_code == 200:
        # Looking for a price class, often tv-symbol-price-quote__value or similar
        m = re.search(r'last-price-value.*?>(.*?)<', r.text)
        if hasattr(m, 'group'):
            print("Regex match (last-price-value):", m.group(1))
        
        # Searching for any number near "Bullish"
        m2 = re.search(r'>([^<]+)<\/span>[^\w]*Bullish', r.text)
        print("Regex match near Bullish:", m2.group(1) if m2 else "None")
        
        # Direct search for typical price formatting
        m3 = re.search(r'data-symbol="AAII:BULLISH".*?(\d{1,2}\.?\d*)', r.text, re.DOTALL)
        print("Regex match data-symbol AAII:BULLISH:", m3.group(1) if m3 else "None")
except Exception as e:
    print("Error:", e)

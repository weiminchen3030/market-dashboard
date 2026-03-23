"""Test alternative data sources for AAII, NYMO, and US Liquidity"""
import requests
import json

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 1. AAII Sentiment - public JS file they maintain
print("=== AAII ===")
try:
    res = requests.get("https://www.aaii.com/files/surveys/sentiment.js", headers=HEADERS, timeout=10)
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Content (first 300 chars):", res.text[:300])
except Exception as e:
    print("Error:", e)

# 2. NYMO via Stooq
print("\n=== NYMO via Stooq ===")
try:
    res = requests.get("https://stooq.com/q/d/l/?s=%24nymo&i=d&d1=20260301&d2=20260323", headers=HEADERS, timeout=10)
    print("Status:", res.status_code)
    print("Content:", res.text[:300])
except Exception as e:
    print("Error:", e)

# 3. US Net Liquidity via FRED (Federal Reserve)
#    Net Liquidity = Fed Balance Sheet (WALCL) - TGA (WTREGEN) - ON RRP (RRPONTSYD)
print("\n=== FRED API (US Liquidity) ===")
try:
    # FRED has a free API with no key for basic data
    base = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    # Fed total assets (weekly)
    for series_id, name in [("WALCL", "Fed Balance Sheet"), ("WTREGEN", "TGA"), ("RRPONTSYD", "ON RRP")]:
        r = requests.get(f"{base}?id={series_id}", headers=HEADERS, timeout=10)
        print(f"{name} ({series_id}): status={r.status_code}, last 100 chars: {r.text[-100:]}")
except Exception as e:
    print("FRED Error:", e)

# 4. Crypto Fear & Greed (we already have this, just confirming)
print("\n=== Crypto FnG ===")
try:
    res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
    print(res.json())
except Exception as e:
    print("Error:", e)

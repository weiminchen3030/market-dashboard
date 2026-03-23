import requests
import re
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for sym in ['BULLISH', 'BEARISH', 'NEUTRAL']:
    r = requests.get(f'https://www.tradingview.com/symbols/AAII-{sym}/', headers=HEADERS, timeout=10)
    
    # We found earlier that 'last-price-value' or 'data-symbol="AAII:BULLISH"' might be present.
    # Let's check all numbers that look like percentages.
    m1 = re.search(rf'data-symbol="AAII:{sym}".*?(\d{{1,2}}\.\d{{2}})', r.text, re.DOTALL)
    m2 = re.search(r'last-price-value.*?>(.*?)<', r.text)
    m3 = re.search(r'\"price\":\s*([\d\.]+)', r.text)
    
    print(f"--- {sym} ---")
    print("data-symbol:", m1.group(1) if m1 else "No")
    print("last-price :", m2.group(1) if m2 else "No")
    print("json price :", m3.group(1) if m3 else "No")

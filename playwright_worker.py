"""
playwright_worker.py  –  runs in a separate subprocess (avoids Streamlit event-loop conflict)
Scrapes: Trading Logic, CNN F&G, Truflation, AAII
Outputs: JSON to stdout
"""
import sys, json, re

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(json.dumps({
        "TradingLogic": "N/A", "CNNFearGreed": "N/A",
        "Truflation": "N/A",
        "AAII": {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"},
    }))
    sys.exit(0)

import subprocess
# Auto-install chromium for Streamlit Cloud deployments
try:
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
    pass

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

results = {
    "TradingLogic": "N/A",
    "CNNFearGreed": "N/A",
    "Truflation":   "N/A",
    "AAII": {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"},
}

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx  = browser.new_context(user_agent=UA, locale='en-US')
        page = ctx.new_page()

        # ── 1. Trading Logic ──────────────────────────────────────────────────
        try:
            page.goto("https://www.trading-logic.com/en",
                      timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            text = page.inner_text("body")
            # "Total Score\n272 / 1100"
            m = re.search(r'Total Score\s*\n\s*(\d+)\s*/', text)
            if m:
                results["TradingLogic"] = m.group(1)
            else:
                m = re.search(r'Total Score[^\d]{0,10}(\d{2,4})', text)
                if m:
                    results["TradingLogic"] = m.group(1)
        except Exception:
            pass

        # ── 2. CNN Fear & Greed ───────────────────────────────────────────────
        try:
            page.goto("https://www.cnn.com/markets/fear-and-greed",
                      timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            elem = page.query_selector('.market-fng-gauge__dial-number-value')
            if elem:
                results["CNNFearGreed"] = elem.inner_text().strip()
            else:
                text = page.inner_text("body")
                m = re.search(r'(\d{1,2})\s*\n\s*(?:Extreme )?(?:Fear|Greed)', text)
                if m:
                    results["CNNFearGreed"] = m.group(1)
        except Exception:
            pass

        # ── 3. Truflation CPI ─────────────────────────────────────────────────
        try:
            page.goto("https://truflation.com/marketplace/us-inflation-rate",
                      timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(4000)
            text = page.inner_text("body")
            m = re.search(r'Year over year change updating daily\s*\n\s*([\d.]+%?)', text)
            if m:
                results["Truflation"] = m.group(1)
            else:
                m = re.search(r'([\d]+\.[\d]+%?)\s*\n\s*-[\d.]+', text)
                if m:
                    results["Truflation"] = m.group(1)
        except Exception:
            pass

        # ── 4. AAII Sentiment Survey via TradingView ───────────────────────────
        try:
            for sym, key in [("BULLISH", "Bullish"), ("BEARISH", "Bearish")]:
                page.goto(f"https://www.tradingview.com/symbols/AAII-{sym}/",
                          timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(3000)
                text = page.inner_text("body")
                # Pattern: literal symbol name followed by the number on the next line
                m = re.search(rf'{sym}\n([\d\.]+)\n', text)
                if m:
                    results["AAII"][key] = m.group(1) + "%"
            
            # Neutral is usually 100 - Bullish - Bearish
            bull = results["AAII"]["Bullish"].replace('%', '')
            bear = results["AAII"]["Bearish"].replace('%', '')
            if bull != "N/A" and bear != "N/A":
                neut = 100.0 - float(bull) - float(bear)
                results["AAII"]["Neutral"] = f"{neut:.2f}%"
        except Exception:
            pass

        browser.close()

except Exception:
    pass

print(json.dumps(results))

import re
from playwright.sync_api import sync_playwright

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def run_playwright_dbg():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=HEADERS['User-Agent'])
        page = context.new_page()

        print("--- MacroMicro AAII ---")
        try:
            page.goto("https://en.macromicro.me/charts/20828/us-aaii-sentimentsurvey", timeout=15000)
            page.wait_for_timeout(5000)
            text = page.inner_text("body")
            print(text[:2000].replace('\n', ' | '))
            
            # extract bearish, neutral, bullish
            bull = re.search(r'Bullish\s*[\n\|]?\s*(\d{1,2}\.?\d*%)?', text, re.IGNORECASE)
            print("Bullish match:", bull)
        except Exception as e:
            print("Error MM AAII:", e)
            
        print("--- MacroMicro Liquidity ---")
        try:
            page.goto("https://en.macromicro.me/charts/119769/US-Liquidity-Index", timeout=15000)
            page.wait_for_timeout(5000)
            text = page.inner_text("body")
            print(text[:2000].replace('\n', ' | '))
        except Exception as e:
            print("Error MM Liq:", e)

        browser.close()

if __name__ == "__main__":
    run_playwright_dbg()

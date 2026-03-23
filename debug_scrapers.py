from playwright.sync_api import sync_playwright

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent=HEADERS['User-Agent'])
    page = context.new_page()

    with open("debug_output.txt", "w", encoding="utf-8") as f:
        f.write("--- TRADING LOGIC ---\n")
        page.goto("https://www.trading-logic.com/en", timeout=15000)
        page.wait_for_timeout(3000)
        f.write(page.inner_text("body")[:1000] + "\n")

        f.write("\n--- AAII ---\n")
        page.goto("https://www.aaii.com/sentimentsurvey", timeout=15000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        idx = text.lower().find('bullish')
        if idx != -1:
            f.write(text[max(0, idx-100):idx+500] + "\n")

        f.write("\n--- TRUFLATION ---\n")
        page.goto("https://truflation.com/marketplace/us-inflation-rate", timeout=15000)
        page.wait_for_timeout(5000)
        text = page.inner_text("body")
        idx = text.lower().find('cpi')
        if idx != -1:
            f.write(text[max(0, idx-100):idx+500] + "\n")

    browser.close()

"""Quick debug: dump Trading Logic body text to file"""
from playwright.sync_api import sync_playwright
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(user_agent=UA).new_page()
    page.goto("https://www.trading-logic.com/en", timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(4000)
    text = page.inner_text("body")
    browser.close()

with open("tl_debug.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("Written tl_debug.txt, length:", len(text))

import requests
from bs4 import BeautifulSoup
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def test_trading_logic():
    print("--- Trading Logic ---")
    url = "https://www.trading-logic.com/en"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    # Try to find Breadth
    # Usually it's in a table or a specific div
    texts = soup.stripped_strings
    for text in texts:
        if "breadth" in text.lower():
            print("FOUND BREADTH CONTEXT:", text)

def test_naaim():
    print("--- NAAIM ---")
    url = "https://naaim.org/programs/naaim-exposure-index/"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    # The table usually has the latest date and value
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    if tables:
        rows = tables[0].find_all('tr')
        for i, row in enumerate(rows[:5]):
            cols = [col.text.strip() for col in row.find_all(['th', 'td'])]
            print(f"Row {i}: {cols}")

def test_aaii():
    print("--- AAII ---")
    url = "https://www.aaii.com/sentimentsurvey"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    for t in tables[:2]:
        print("TABLE:", t.text[:200].replace('\n', ' '))

def test_cnn():
    print("--- CNN Fear & Greed ---")
    url = "https://www.cnn.com/markets/fear-and-greed"
    res = requests.get(url, headers=HEADERS)
    # The score is often in a specific div, e.g., "market-fng-gauge__dial-number-value"
    soup = BeautifulSoup(res.text, 'html.parser')
    score_element = soup.find('span', class_=re.compile(r'dial-number', re.I))
    if score_element:
        print("Score element found:", score_element.text)
    else:
        print("Score not found by class, looking for Fear & Greed string")
        for text in list(soup.stripped_strings)[:50]:
            if "fear" in text.lower() or "greed" in text.lower():
                print(text)

def test_truflation():
    print("--- Truflation ---")
    url = "https://truflation.com/marketplace/us-inflation-rate"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    texts = list(soup.stripped_strings)
    for i, t in enumerate(texts):
        if "US CPI" in t or "Inflation Rate" in t or "%" in t:
            print(f"Text {i}: {t}")
            if i > 50: break

if __name__ == "__main__":
    test_trading_logic()
    test_naaim()
    test_aaii()
    test_cnn()
    test_truflation()

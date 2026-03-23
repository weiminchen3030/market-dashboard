import requests
from bs4 import BeautifulSoup
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def test_cnn():
    print("Testing CNN...")
    try:
        res = requests.get('https://production.api.cnn.io/metrics/quotes/indices?quotes=VIX,VVIX&apikey=test', headers=headers, timeout=10) # Maybe CNN API? No, the fear and greed is different. Let's just try the main URL.
        res = requests.get('https://www.cnn.com/markets/fear-and-greed', headers=headers, timeout=10)
        print("Status CNN F&G:", res.status_code)
    except Exception as e:
        print("Error:", e)

def test_truflation():
    print("Testing Truflation...")
    try:
        res = requests.get('https://truflation.com/marketplace/us-inflation-rate', headers=headers, timeout=10)
        print("Status Truflation:", res.status_code)
    except Exception as e:
        print("Error:", e)
        
def test_macromicro():
    print("Testing MacroMicro...")
    try:
        res = requests.get('https://sc.macromicro.me/charts/80362/mei-guo-shi-chang-jing-liu-dong-xing', headers=headers, timeout=10)
        print("Status MacroMicro:", res.status_code)
    except Exception as e:
        print("Error:", e)

def test_stockcharts():
    print("Testing StockCharts NYMO...")
    try:
        res = requests.get('https://stockcharts.com/sc3/ui/?s=%24NYMO', headers=headers, timeout=10)
        print("Status StockCharts:", res.status_code)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_cnn()
    test_truflation()
    test_macromicro()
    test_stockcharts()

"""Test alternative sources for AAII and US Liquidity"""
import requests, json, re, io
import pandas as pd

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ── AAII alternatives ──────────────────────────────────────────────────────────

print("=== AAII alternatives ===")

# 1. StockCharts public data for AAII
try:
    r = requests.get("https://stockcharts.com/c-sc/sc?s=%24BPSPX&p=W&b=5&g=0&i=0", headers=HEADERS, timeout=10)
    print("StockCharts status:", r.status_code)
except Exception as e:
    print("StockCharts err:", e)

# 2. Try MacroMicro API endpoint (they expose chart data as JSON)
for chart_id in ["20828"]:
    try:
        r = requests.get(f"https://en.macromicro.me/charts/data/{chart_id}", headers=HEADERS, timeout=10)
        print(f"MacroMicro API {chart_id}: status={r.status_code}, content[:200]={r.text[:200]}")
    except Exception as e:
        print(f"MacroMicro {chart_id} err:", e)

# 3. Stooq AAII data (they sometimes carry sentiment)
try:
    r = requests.get("https://stooq.com/q/d/l/?s=aaii-bull&i=w", headers=HEADERS, timeout=10)
    print("Stooq AAII-bull:", r.status_code, r.text[:200])
except Exception as e:
    print("Stooq err:", e)

# 4. Try direct AAII endpoint with session/cookies approach
try:
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get("https://www.aaii.com/sentimentsurvey", timeout=10)
    print("AAII direct status:", r.status_code, "content len:", len(r.text))
    # Check if there's useful data
    if "Bullish" in r.text:
        # Try to find percentage near "Bullish"
        m = re.search(r'Bullish.*?(\d{1,2}\.\d+)%', r.text[:5000], re.DOTALL)
        print("AAII bullish match:", m.group(0) if m else "No match")
    else:
        print("No 'Bullish' keyword found in response")
except Exception as e:
    print("AAII err:", e)

# ── US Liquidity / FRED ────────────────────────────────────────────────────────
print("\n=== FRED US Liquidity ===")

def fetch_fred(series_id, timeout=30):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    df = pd.read_csv(io.StringIO(r.text), parse_dates=['DATE'])
    df = df[df.iloc[:, 1] != '.'].copy()
    df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1])
    df.set_index('DATE', inplace=True)
    df.columns = [series_id]
    return df

try:
    walcl = fetch_fred("WALCL")
    print("WALCL latest:", walcl.tail(2))
except Exception as e:
    print("WALCL err:", e)

try:
    wtregen = fetch_fred("WTREGEN")
    print("WTREGEN latest:", wtregen.tail(2))
except Exception as e:
    print("WTREGEN err:", e)

try:
    rrpon = fetch_fred("RRPONTSYD")
    print("RRPONTSYD latest:", rrpon.tail(2))
except Exception as e:
    print("RRPONTSYD err:", e)

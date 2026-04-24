import yfinance as yf
import pandas as pd
import requests
import logging
import datetime
import time
import os
import streamlit as st
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback API Keys
FINNHUB_API_KEY = "d6s47vpr01qrb5i8igb0d6s47vpr01qrb5i8igbg"
ALPHAVANTAGE_API_KEY = "FNCNL30HQWCWIC0G"

# Cloud Database configurations (Streamlit Secrets / ENV vars)
# Attempt to read from Streamlit Secrets securely, otherwise fallback to local SQLite
try:
    _db_url = st.secrets["SUPABASE_DATABASE_URI"]
except Exception:
    _db_url = os.environ.get("SUPABASE_DATABASE_URI", "sqlite:///stock_cache.db")

DATABASE_URL = _db_url
engine = create_engine(DATABASE_URL)

def init_db():
    with engine.begin() as conn:
        # Compatible with both Postgres and SQLite
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS daily_prices (
                Symbol VARCHAR(20),
                Date VARCHAR(20),
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume BIGINT,
                PRIMARY KEY (Symbol, Date)
            )
        '''))

def get_cached_date_range(symbol):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT MIN(Date), MAX(Date) FROM daily_prices WHERE Symbol = :sym"), {"sym": symbol})
        val = res.fetchone()
        if val and val[0] and val[1]:
            return val[0], val[1]
        return None, None

def get_cached_data(symbol, start_date=None, end_date=None):
    query = "SELECT Date, Open, High, Low, Close, Volume FROM daily_prices WHERE Symbol = :sym"
    params = {"sym": symbol}
    
    if start_date:
        query += " AND Date >= :start"
        params["start"] = start_date.strftime("%Y-%m-%d")
    if end_date:
        query += " AND Date <= :end"
        params["end"] = end_date.strftime("%Y-%m-%d")
        
    with engine.connect() as conn:
        df = pd.read_sql_query(text(query), conn, params=params, index_col='Date', parse_dates=['Date'])
    return format_df_for_compat(df)

def save_to_cache(symbol, df):
    if df is None or df.empty:
        return
        
    df_to_save = df.copy()
    df_to_save['Symbol'] = symbol
    # Guarantee string format for standard cross-DB persistence
    df_to_save['Date'] = df_to_save.index.strftime('%Y-%m-%d') 
    
    # Primitive upsert: Delete trailing overlapping timeframe for safety, then bulk insert
    min_date = df_to_save['Date'].min()
    
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM daily_prices WHERE Symbol = :sym AND Date >= :min_date"),
                     {"sym": symbol, "min_date": min_date})
                     
    # Push entirely fresh chunk
    df_to_save.to_sql('daily_prices', con=engine, if_exists='append', index=False, method='multi')

def format_df_for_compat(df):
    """Ensure the DataFrame matches YFinance output conventions."""
    if df is None or df.empty:
        return df
    
    # Ensure Index is Datetime and tz-naive
    df.index = pd.to_datetime(df.index)
    if df.index.tzinfo is not None:
        df.index = df.index.tz_localize(None)
    df.sort_index(inplace=True)
    
    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
    return df[cols]

def fetch_finnhub(symbol, start_date=None, end_date=None):
    """Fallback 1: Finnhub Candles"""
    logger.info(f"Fallback Finnhub: Fetching {symbol}")
    
    if end_date is None:
        end_date = datetime.datetime.now()
    if start_date is None:
        start_date = end_date - datetime.timedelta(days=365)
        
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    
    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={start_ts}&to={end_ts}&token={FINNHUB_API_KEY}"
    res = requests.get(url, timeout=10)
    
    if res.status_code == 200:
        data = res.json()
        if data.get('s') == 'ok':
            df = pd.DataFrame({
                'Open': data['o'],
                'High': data['h'],
                'Low': data['l'],
                'Close': data['c'],
                'Volume': data['v']
            })
            df.index = pd.to_datetime(data['t'], unit='s')
            return format_df_for_compat(df)
        elif data.get('s') == 'no_data':
            return pd.DataFrame()
            
    if res.status_code == 429: # Rate limit
        logger.warning(f"Finnhub rate limit hit for {symbol}")
        
    return None

def fetch_alphavantage(symbol):
    """Fallback 2: Alpha Vantage (Daily Standard)"""
    logger.info(f"Fallback Alpha Vantage: Fetching {symbol}")
    
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={ALPHAVANTAGE_API_KEY}"
    res = requests.get(url, timeout=10)
    
    if res.status_code == 200:
        data = res.json()
        time_series = data.get("Time Series (Daily)", {})
        if time_series:
            rows = []
            for date_str, metrics in time_series.items():
                rows.append({
                    'Date': pd.to_datetime(date_str),
                    'Open': float(metrics.get("1. open", 0)),
                    'High': float(metrics.get("2. high", 0)),
                    'Low': float(metrics.get("3. low", 0)),
                    'Close': float(metrics.get("4. close", 0)),
                    'Volume': int(metrics.get("5. volume", 0)) 
                })
            df = pd.DataFrame(rows).set_index('Date')
            return format_df_for_compat(df)
            
    if "Information" in res.json() and "rate limit" in str(res.json().get("Information", "")).lower():
         logger.warning(f"Alpha Vantage rate limit hit for {symbol}")
         time.sleep(2) 
         
    return None

def _fetch_from_apis(symbol, start_date, end_date):
    """Orchestrates actual network fetches using fallbacks."""
    # 1. Attempt YFinance Native
    try:
        ticker = yf.Ticker(symbol)
        df_yf = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        if not df_yf is None and not df_yf.empty and len(df_yf) > 0:
            return format_df_for_compat(df_yf)
    except Exception as e:
        logger.warning(f"YFinance fetch failed for {symbol}: {e}")

    # Fallback Mechanisms (Exclude Indices mapping failures)
    is_index = '^' in symbol or symbol in ['VIX', 'VVIX'] 
    
    if not is_index:
        # 2. Attempt Finnhub
        df_finnhub = fetch_finnhub(symbol, start_date, end_date)
        if df_finnhub is not None and not df_finnhub.empty:
            df_finnhub = df_finnhub[(df_finnhub.index >= pd.to_datetime(start_date).tz_localize(None)) & 
                                    (df_finnhub.index <= pd.to_datetime(end_date).tz_localize(None))]
            if not df_finnhub.empty: return df_finnhub
            
        # 3. Attempt Alpha Vantage
        df_av = fetch_alphavantage(symbol)
        if df_av is not None and not df_av.empty:
            df_av = df_av[(df_av.index >= pd.to_datetime(start_date).tz_localize(None)) & 
                          (df_av.index <= pd.to_datetime(end_date).tz_localize(None))]
            if not df_av.empty: return df_av

    return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

def get_stock_data(symbol, start_date=None, end_date=None, period="1y"):
    """
    Intelligent read-through cache fetcher connected via SQLAlchemy.
    """
    init_db()
    
    now = datetime.datetime.now()
    if end_date is None:
        end_date = now
        
    if start_date is None:
        if period == "1y":
            start_date = end_date - datetime.timedelta(days=365)
        elif period == "2d":
            start_date = end_date - datetime.timedelta(days=2)
        elif period == "3y":
            start_date = end_date - datetime.timedelta(days=365*3)
        elif period == "1mo":
            start_date = end_date - datetime.timedelta(days=30)
        else:
            start_date = end_date - datetime.timedelta(days=365)
            
    # Normalize formats
    try:
        start_date = pd.to_datetime(start_date).tz_localize(None)
        end_date = pd.to_datetime(end_date).tz_localize(None)
    except Exception as e:
        logger.error(f"Date conversion error: {e}")
        pass
        
    min_date_str, max_date_str = get_cached_date_range(symbol)
    
    if max_date_str and min_date_str:
        max_date = pd.to_datetime(max_date_str)
        min_date = pd.to_datetime(min_date_str)
        
        # Check if the cache is missing data on either boundary
        missing_future = max_date < (end_date - datetime.timedelta(days=1))
        missing_past = min_date > (start_date + datetime.timedelta(days=1))
        
        if missing_past:
            logger.info(f"[{symbol}] Cache missing backward history. Fetching full requested history.")
            new_data = _fetch_from_apis(symbol, start_date, end_date + datetime.timedelta(days=1))
            if new_data is not None and not new_data.empty:
                save_to_cache(symbol, new_data)
        elif missing_future:
            logger.info(f"[{symbol}] Cache partial hit. Fetching delta from {max_date_str} to {end_date.strftime('%Y-%m-%d')}")
            delta_start = max_date + datetime.timedelta(days=1)
            new_data = _fetch_from_apis(symbol, delta_start, end_date + datetime.timedelta(days=1)) # API end exclusive padding
            if new_data is not None and not new_data.empty:
                save_to_cache(symbol, new_data)
        else:
            logger.info(f"[{symbol}] Cache full hit. Minimal latency via Database.")
            
    else:
        logger.info(f"[{symbol}] Cache miss. Fetching full requested history from APIs into Database.")
        new_data = _fetch_from_apis(symbol, start_date, end_date + datetime.timedelta(days=1))
        if new_data is not None and not new_data.empty:
            save_to_cache(symbol, new_data)
            
    # Read the final chunk exactly requested from DB
    final_df = get_cached_data(symbol, start_date, end_date)
    
    if final_df is None or final_df.empty:
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        
    return final_df

if __name__ == "__main__":
    print(f"Engine instantiated as: {engine}")
    
    # Remove old dev DB if exists
    if str(engine.url).startswith("sqlite") and os.path.exists('stock_cache.db'):
        os.remove('stock_cache.db')
        
    print("Testing Cache Initialization...")
    df_missing = get_stock_data("AAPL", period="1mo")
    print(f"First Fetch Rows: {len(df_missing)}")
    
    print("\nTesting Cache Full Hit...")
    start_time = time.time()
    df_hit = get_stock_data("AAPL", period="1mo")
    print(f"Hit Time: {time.time()-start_time:.5f}s, Rows: {len(df_hit)}")

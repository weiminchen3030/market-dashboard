import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import time

from scrapers import get_vix_data, get_crypto_fng, get_naaim, scrape_with_playwright
from market_screener import run_screener, calculate_indicators, SP500_LIST, NASDAQ100_LIST, WATCH_LIST
from data_fetcher import get_stock_data
from demark_backtest import calc_ma, calc_demark, calc_rsi, backtest_dca

app = FastAPI(
    title="Market Screener API", 
    description="Backend API for quantitative stock scanning and alerts.",
    version="1.0.0"
)

# Set up CORS allowing all origins to facilitate frontend/mobile connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScreenerRequest(BaseModel):
    tickers: List[str]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "FastAPI engine is active and serving requests!"}

@app.get("/api/market/vix")
def fetch_vix():
    try:
        data = get_vix_data()
        if not data or data.get('VIX') == "N/A":
            raise HTTPException(status_code=503, detail="Failed to retrieve VIX")
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/dashboard")
def fetch_dashboard():
    try:
        naaim      = get_naaim()
        crypto_fng = get_crypto_fng()
        vix_data   = get_vix_data()
        pw         = scrape_with_playwright()
        
        return {
            "naaim": naaim,
            "crypto_fng": crypto_fng, 
            "vix_data": vix_data,
            "playwright_data": pw
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/market/screener")
def scan_tickers(req: ScreenerRequest):
    if not req.tickers:
        raise HTTPException(status_code=400, detail="Ticker list cannot be empty")
    try:
        df = run_screener(req.tickers)
        if df.empty:
            return {"signals": []}
        return {"signals": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

_SCREENER_CACHE = {}
_CACHE_TTL = 3600  # 1 hour

@app.get("/api/market/screener/index/{universe}")
def scan_universe(universe: str, date: str = None):
    symbols = WATCH_LIST
    if universe == "SP500": symbols = SP500_LIST
    elif universe == "NASDAQ100": symbols = NASDAQ100_LIST
    
    cache_key = f"{universe}_{date}"
    now = time.time()
    
    if cache_key in _SCREENER_CACHE:
        cached_result, timestamp = _SCREENER_CACHE[cache_key]
        if now - timestamp < _CACHE_TTL:
            return {"signals": cached_result, "cached": True}
    
    try:
        t_date = datetime.strptime(date, "%Y-%m-%d") if date else None
        df = run_screener(symbols, target_date=t_date)
        if df.empty:
            return {"signals": [], "cached": False}
            
        result_dict = df.to_dict(orient="records")
        _SCREENER_CACHE[cache_key] = (result_dict, now)
        return {"signals": result_dict, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/stock/{ticker}")
def fetch_stock_overview(ticker: str):
    ticker = ticker.upper()
    try:
        info = yf.Ticker(ticker).info
        if not info or ('longBusinessSummary' not in info and 'description' not in info):
            profile = None
        else:
            profile = {
                'name': info.get('shortName', info.get('longName', ticker)),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'summary': info.get('longBusinessSummary', info.get('description', 'No description available.')),
                'website': info.get('website', ''),
                'marketCap': info.get('marketCap', None),
                'trailingPE': info.get('trailingPE', None),
                'forwardPE': info.get('forwardPE', None),
                'dividendYield': info.get('dividendYield', None),
                'beta': info.get('beta', None),
                'priceToBook': info.get('priceToBook', None),
                'trailingEps': info.get('trailingEps', None),
                'targetMeanPrice': info.get('targetMeanPrice', None)
            }
            
        end_str = datetime.now().strftime('%Y-%m-%d')
        start_str = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        raw_df = get_stock_data(ticker, start_date=start_str, end_date=end_str)
        
        latest_data = {}
        if raw_df is not None and not raw_df.empty:
            df_ind = calculate_indicators(raw_df)
            last_row = df_ind.iloc[-1]
            latest_data = {
                "price": last_row['Close'],
                "macd": last_row['MACD'],
                "rsi": last_row['RSI'],
            }
            
        return {
            "symbol": ticker,
            "profile": profile,
            "latest_technicals": latest_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/stock/{ticker}/history")
def fetch_stock_history(ticker: str):
    ticker = ticker.upper()
    try:
        end_str = datetime.now().strftime('%Y-%m-%d')
        start_str = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        raw_df = get_stock_data(ticker, start_date=start_str, end_date=end_str)
        
        if raw_df is None or raw_df.empty:
            raise HTTPException(status_code=404, detail="No historical data found")
            
        df = calculate_indicators(raw_df)
        
        # Calculate Is_Buy and Is_Sell
        is_buy = (
            (df["EMA5"] > df["EMA13"]) & (df["MACD"] < 0) & (df["Signal_Line"] < 0) & 
            (df["MACD"] > df["Signal_Line"]) & (df["EMA233_Slope"] > 0) & 
            (df["Close"].shift(1) > df["LowLevel"].shift(1)) & (df["RSI"].shift(1) > df["RSI"].shift(2))
        )
        is_sell = (
            (df["EMA5"] < df["EMA13"]) & (df["MACD"] > 0) & (df["Signal_Line"] > 0) & 
            (df["MACD"] < df["Signal_Line"]) & (df["EMA233_Slope"] < 0) & 
            (df["Close"].shift(1) < df["HighLevel"].shift(1)) & (df["RSI"].shift(1) < df["RSI"].shift(2))
        )
        df["Is_Buy"] = is_buy
        df["Is_Sell"] = is_sell
        
        # Return tail 200 for frontend chart rendering
        chart_df = df.tail(200).reset_index()
        chart_df["Date"] = chart_df["Date"].dt.strftime("%Y-%m-%d")
        
        records = chart_df[["Date", "Open", "High", "Low", "Close", "Is_Buy", "Is_Sell", "EMA5", "EMA13"]].to_dict(orient="records")
        return {"data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/breadth")
def fetch_signal_breadth(universe: str = "SP500", years: int = 3):
    try:
        symbols = SP500_LIST
        proxy = 'SPY'
        if universe == "NASDAQ100":
            symbols = NASDAQ100_LIST
            proxy = 'QQQ'
        elif universe == "CUSTOM":
            symbols = WATCH_LIST
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        fetch_start = start_date - timedelta(days=365)
        
        buy_series = []
        sell_series = []
        
        for sym in symbols[:150]: # Capping at 150 for speedy response testing
            df = get_stock_data(sym, start_date=fetch_start.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
            if df is not None and len(df) >= 233:
                df = calculate_indicators(df)
                is_buy = (
                    (df["EMA5"] > df["EMA13"]) & (df["MACD"] < 0) & (df["Signal_Line"] < 0) & 
                    (df["MACD"] > df["Signal_Line"]) & (df["EMA233_Slope"] > 0) & 
                    (df["Close"].shift(1) > df["LowLevel"].shift(1)) & (df["RSI"].shift(1) > df["RSI"].shift(2))
                )
                is_sell = (
                    (df["EMA5"] < df["EMA13"]) & (df["MACD"] > 0) & (df["Signal_Line"] > 0) & 
                    (df["MACD"] < df["Signal_Line"]) & (df["EMA233_Slope"] < 0) & 
                    (df["Close"].shift(1) < df["HighLevel"].shift(1)) & (df["RSI"].shift(1) < df["RSI"].shift(2))
                )
                b = is_buy.fillna(False).astype(int)
                s = is_sell.fillna(False).astype(int)
                if not b.empty:
                    buy_series.append(b)
                    sell_series.append(s)
                    
        if not buy_series:
            return {"breadth": [], "proxy": [], "proxySymbol": proxy}
            
        df_buys = pd.concat(buy_series, axis=1).sum(axis=1)
        df_sells = pd.concat(sell_series, axis=1).sum(axis=1)
        
        breadth_df = pd.DataFrame({'Buys': df_buys, 'Sells': df_sells})
        breadth_df = breadth_df[breadth_df.index >= start_date]
        
        proxy_df = get_stock_data(proxy, start_date=(start_date - timedelta(days=10)).strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        proxy_df = proxy_df[proxy_df.index >= start_date]
        
        breadth_df = breadth_df.reset_index()
        breadth_df["Date"] = breadth_df["Date"].dt.strftime("%Y-%m-%d")
        proxy_df = proxy_df.reset_index()
        proxy_df["Date"] = proxy_df["Date"].dt.strftime("%Y-%m-%d")
        
        return {
            "breadth": breadth_df[["Date", "Buys", "Sells"]].to_dict(orient="records"),
            "proxy": proxy_df[["Date", "Close", "Open", "High", "Low"]].to_dict(orient="records"),
            "proxySymbol": proxy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/strategy/{ticker}")
def run_strategy(ticker: str, lev_ticker: str = "UPRO", years: int = 10, monthly_investment: float = 500.0):
    ticker = ticker.upper()
    lev_ticker = lev_ticker.upper()
    try:
        end_date = datetime.now()
        test_start_date = end_date - timedelta(days=365 * years)
        fetch_start_date = test_start_date - timedelta(days=200)

        df = get_stock_data(ticker, start_date=fetch_start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        vix_df = get_stock_data('^VIX', start_date=fetch_start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        lev_df = get_stock_data(lev_ticker, start_date=fetch_start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"Failed to fetch base ticker {ticker}")
            
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        if isinstance(vix_df.columns, pd.MultiIndex): vix_df.columns = vix_df.columns.droplevel(1)
        if isinstance(lev_df.columns, pd.MultiIndex): lev_df.columns = lev_df.columns.droplevel(1)
            
        df['VIX'] = vix_df['Close'].ffill()
        df['Lev_Open'] = lev_df['Open'].ffill()
        df['Lev_High'] = lev_df['High'].ffill()
        df['Lev_Low'] = lev_df['Low'].ffill()
        df['Lev_Close'] = lev_df['Close'].ffill()
        
        df = calc_ma(df)
        df = calc_demark(df)
        df = calc_rsi(df)
        
        df = df[df.index >= test_start_date]
        df.dropna(inplace=True)
        
        fe, fbe, si, bi, tr, br, history, df_backtested = backtest_dca(df, monthly_injection=monthly_investment)
        
        # Prepare chart representation
        df_chart = df_backtested.reset_index()
        df_chart["Date"] = df_chart["Date"].dt.strftime("%Y-%m-%d")
        
        # History trade dates to string
        for idx in range(len(history)):
            if isinstance(history[idx]["Date"], pd.Timestamp):
                history[idx]["Date"] = history[idx]["Date"].strftime("%Y-%m-%d")
        
        chart_records = df_chart[["Date", "Close", "Lev_Close", "Equity", "Baseline_Equity", "Cash_Balance_Curve", "VIX"]].to_dict(orient="records")
        
        return {
            "metrics": {
                "base_ticker": ticker,
                "lev_ticker": lev_ticker,
                "cash_out_of_pocket": si,
                "base_dca_output": fbe,
                "base_return": br,
                "strategy_output": fe,
                "strategy_return": tr,
                "excess_alpha": fe - fbe
            },
            "history": history,
            "chart": chart_records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

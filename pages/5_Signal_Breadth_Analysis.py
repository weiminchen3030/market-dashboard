import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

from market_screener import SP500_LIST, NASDAQ100_LIST, WATCH_LIST, calculate_indicators
from data_fetcher import get_stock_data

st.set_page_config(page_title="Market Breadth Analysis", page_icon="📡", layout="wide")

st.title("📡 Market Signal Breadth")
st.markdown("Analyze macroscopic market extremes by visually aggregating total incoming Buy and Sell Signals across every individual stock within a major index on a daily basis. Historical clusters of Buy signals often tightly correlate with systemic market bottoms.")

st.divider()

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    universe = st.selectbox("Select Universe", ["S&P 500", "NASDAQ 100", "Custom Watchlist"])
with col2:
    years = st.slider("Lookback Period (Years)", min_value=1, max_value=10, value=3)

def compute_signals(df):
    if df is None or df.empty or len(df) < 233:
        return pd.Series(dtype=int), pd.Series(dtype=int)
    
    df = df.copy()
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
    
    return is_buy.fillna(False).astype(int), is_sell.fillna(False).astype(int)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_and_aggregate_breadth(universe_name, years_lookback):
    if universe_name == "S&P 500":
        symbols = SP500_LIST
        proxy = 'SPY'
    elif universe_name == "NASDAQ 100":
        symbols = NASDAQ100_LIST
        proxy = 'QQQ'
    else:
        symbols = WATCH_LIST
        proxy = 'SPY'
        
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=365 * years_lookback)
    fetch_start = start_date - datetime.timedelta(days=365) # Buffer for 233 EMA
    
    buy_series = []
    sell_series = []
    
    progress_bar = st.progress(0, text=f"Aggregating {len(symbols)} tickers. This may take up to 20 seconds...")
    total = len(symbols)
    
    for i, sym in enumerate(symbols):
        progress_bar.progress((i + 1) / total, text=f"Analyzing {sym} ({i+1}/{total})")
        df = get_stock_data(sym, start_date=fetch_start, end_date=end_date)
        b, s = compute_signals(df)
        if not b.empty:
            buy_series.append(b)
            sell_series.append(s)
            
    progress_bar.empty()
    
    if not buy_series:
        return pd.DataFrame(), pd.DataFrame(), proxy
        
    # Sum across all lists. Using pandas built-in addition on unaligned indices gracefully if we convert to DataFrame.
    # However since all stocks share most dates, let's concat and sum.
    df_buys = pd.concat(buy_series, axis=1).sum(axis=1)
    df_sells = pd.concat(sell_series, axis=1).sum(axis=1)
    
    breadth_df = pd.DataFrame({'Buys': df_buys, 'Sells': df_sells})
    breadth_df = breadth_df[breadth_df.index >= start_date]
    
    proxy_df = get_stock_data(proxy, start_date=start_date - datetime.timedelta(days=10), end_date=end_date)
    proxy_df = proxy_df[proxy_df.index >= start_date]
    
    return breadth_df, proxy_df, proxy

if st.button("🚀 Plot Signal Breadth", type="primary"):
    breadth_df, proxy_df, proxy = fetch_and_aggregate_breadth(universe, years)
    
    if breadth_df.empty or proxy_df.empty:
        st.error("Failed to generate plot data.")
    else:
        # Generate plot
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.04, row_heights=[0.65, 0.35],
            subplot_titles=(f"Market Proxy: {proxy}", "Daily Signal Breadth (Buy = Green, Sell = Red)")
        )
        
        # Row 1: Proxy Candlestick
        fig.add_trace(go.Candlestick(
            x=proxy_df.index,
            open=proxy_df['Open'], high=proxy_df['High'],
            low=proxy_df['Low'], close=proxy_df['Close'],
            name=f"{proxy} Price"
        ), row=1, col=1)
        
        # Row 2: Breadth Bars (Sells as Negative)
        # Note: We plot Sells multiplying by -1 to have them point downwards
        
        fig.add_trace(go.Bar(
            x=breadth_df.index,
            y=breadth_df['Buys'],
            marker_color='#00C076',
            name="Buy Signals",
            opacity=0.85
        ), row=2, col=1)
        
        fig.add_trace(go.Bar(
            x=breadth_df.index,
            y=-breadth_df['Sells'],
            marker_color='#FF4B4B',
            name="Sell Signals",
            opacity=0.85
        ), row=2, col=1)
        
        dt_all = pd.date_range(start=proxy_df.index.min(), end=proxy_df.index.max())
        dt_missing = [d.strftime("%Y-%m-%d") for d in dt_all.difference(proxy_df.index)]
        
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", height=850,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
            margin=dict(l=10, r=10, t=60, b=10), xaxis_rangeslider_visible=False,
            barmode='relative'
        )
        
        fig.update_xaxes(rangebreaks=[dict(values=dt_missing)], showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
        
        st.plotly_chart(fig, use_container_width=True)

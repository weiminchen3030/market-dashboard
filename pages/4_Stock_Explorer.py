import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf

from data_fetcher import get_stock_data

st.set_page_config(page_title="Single Stock Explorer", page_icon="📈", layout="wide")

st.title("📈 Single Stock Explorer")
st.markdown("Instantly pull up technical charts and historical buy/sell signals for any single stock without scanning a full universe.")

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_chart_data(symbol):
    """Fetch 1 year of OHLCV data for charting."""
    end = datetime.now()
    start = end - timedelta(days=365)
    return get_stock_data(symbol, start_date=start, end_date=end)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_company_info(symbol):
    try:
        info = yf.Ticker(symbol).info
        if not info or ('longBusinessSummary' not in info and 'description' not in info):
            return None
        return {
            'name': info.get('shortName', info.get('longName', symbol)),
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
            'trailingEps': info.get('trailingEps', None)
        }
    except Exception:
        return None

def compute_indicators(df):
    """Compute EMAs, MACD, RSI on OHLCV DataFrame."""
    df = df.copy()
    if df.empty: return df
    df["EMA5"]   = df["Close"].ewm(span=5,   adjust=False).mean()
    df["EMA13"]  = df["Close"].ewm(span=13,  adjust=False).mean()
    df["EMA55"]  = df["Close"].ewm(span=55,  adjust=False).mean()
    df["EMA233"] = df["Close"].ewm(span=233, adjust=False).mean()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = df["EMA12"] - df["EMA26"]
    df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD"] - df["Signal_Line"]

    delta = df["Close"].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # Strategy specific for historical markers
    df["HighLevel"] = df["High"].rolling(window=15).max()
    df["LowLevel"] = df["Low"].rolling(window=15).min()
    df["EMA233_Slope"] = df["EMA233"].diff()
    
    df["Is_Buy"] = (
        (df["EMA5"] > df["EMA13"]) & (df["MACD"] < 0) & (df["Signal_Line"] < 0) & 
        (df["MACD"] > df["Signal_Line"]) & (df["EMA233_Slope"] > 0) & 
        (df["Close"].shift(1) > df["LowLevel"].shift(1)) & (df["RSI"].shift(1) > df["RSI"].shift(2))
    )
    
    df["Is_Sell"] = (
        (df["EMA5"] < df["EMA13"]) & (df["MACD"] > 0) & (df["Signal_Line"] > 0) & 
        (df["MACD"] < df["Signal_Line"]) & (df["EMA233_Slope"] < 0) & 
        (df["Close"].shift(1) < df["HighLevel"].shift(1)) & (df["RSI"].shift(1) < df["RSI"].shift(2))
    )
    return df

def build_chart_standalone(symbol):
    raw = fetch_chart_data(symbol)
    if raw is None or raw.empty:
        return None

    df = compute_indicators(raw)
    df = df.tail(180)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.035, row_heights=[0.58, 0.22, 0.20],
        subplot_titles=(f"{symbol}", "MACD", "RSI (14)")
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing_line_color="#26A69A", decreasing_line_color="#EF5350", name="Price", showlegend=False,
    ), row=1, col=1)

    for ema, (color, width) in {"EMA5": ("#F9A825", 1.2), "EMA13": ("#29B6F6", 1.2), "EMA55": ("#AB47BC", 1.5), "EMA233": ("#FF7043", 2.0)}.items():
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema], line=dict(color=color, width=width), name=ema, showlegend=True
        ), row=1, col=1)

    # Plot historical BUY signals
    buy_signals = df[df["Is_Buy"]]
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals["Low"] * 0.95,
            mode="markers",
            marker=dict(symbol="triangle-up", color="#00C076", size=14),
            name="Buy Signal",
            showlegend=False,
            hovertemplate="BUY Signal<extra></extra>"
        ), row=1, col=1)

    # Plot historical SELL signals
    sell_signals = df[df["Is_Sell"]]
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals["High"] * 1.05,
            mode="markers",
            marker=dict(symbol="triangle-down", color="#FF4B4B", size=14),
            name="Sell Signal",
            showlegend=False,
            hovertemplate="SELL Signal<extra></extra>"
        ), row=1, col=1)

    colors_hist = ["#26A69A" if v >= 0 else "#EF5350" for v in df["MACD_Hist"]]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], marker_color=colors_hist, name="MACD Histogram", showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], line=dict(color="#29B6F6", width=1.2), name="MACD", showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal_Line"], line=dict(color="#FF7043", width=1.2, dash="dot"), name="Signal", showlegend=False), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], line=dict(color="#AB47BC", width=1.5), name="RSI", showlegend=False), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="red", width=1, dash="dot"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="green", width=1, dash="dot"), row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)", line_width=0, row=3, col=1)

    dt_all = pd.date_range(start=df.index.min(), end=df.index.max())
    dt_missing = [d.strftime("%Y-%m-%d") for d in dt_all.difference(df.index)]

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", height=780,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        margin=dict(l=10, r=10, t=60, b=10), xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(rangebreaks=[dict(values=dt_missing)], showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig

c1, c2 = st.columns([1, 2])
with c1:
    ticker = st.text_input("Enter a single ticker (e.g. SPY, TSLA, BTC-USD):", value="").upper().strip()

if ticker:
    st.divider()
    with st.spinner(f"Loading data and analyzing {ticker}..."):
        fig = build_chart_standalone(ticker)
        
    if fig:
        st.plotly_chart(fig, use_container_width=True)
        
        info = fetch_company_info(ticker)
        if info:
            st.markdown(f"### About {info['name']}")
            st.caption(f"**Sector:** {info['sector']} | **Industry:** {info['industry']}")
            
            cols = st.columns(6)
            def fmt_mcap(x):
                if x is None: return "N/A"
                if x >= 1e12: return f"${x/1e12:.2f}T"
                if x >= 1e9: return f"${x/1e9:.2f}B"
                if x >= 1e6: return f"${x/1e6:.2f}M"
                return f"${x:,.0f}"
                
            cols[0].metric("Market Cap", fmt_mcap(info.get('marketCap')))
            pe = info.get('trailingPE') or info.get('forwardPE')
            cols[1].metric("P/E Ratio", f"{pe:.2f}" if pe else "N/A")
            cols[2].metric("P/B Ratio", f"{info.get('priceToBook'):.2f}" if info.get('priceToBook') else "N/A")
            cols[3].metric("EPS (TTM)", f"${info.get('trailingEps'):.2f}" if info.get('trailingEps') else "N/A")
            div = info.get('dividendYield')
            cols[4].metric("Div. Yield", f"{div*100:.2f}%" if div else "N/A")
            cols[5].metric("Beta", f"{info.get('beta'):.2f}" if info.get('beta') else "N/A")
            
            st.info(info['summary'])
            if info['website']:
                st.markdown(f"[Visit Website]({info['website']})")
    else:
        st.error(f"Could not retrieve or render chart for {ticker}. Check the ticker symbol.")

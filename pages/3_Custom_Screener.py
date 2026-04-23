import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from market_screener import run_screener
from data_fetcher import get_stock_data

st.set_page_config(page_title="Custom Ticker Screener", page_icon="🔍", layout="wide")

st.title("🔍 Custom Ticker Screener")
st.markdown("Analyze any custom list of stock tickers instantly using the core Screener logic.")
st.info("Input multiple tickers to scan them using the MACD/EMA/RSI strategy engine.")

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_chart_data(symbol):
    """Fetch 1 year of OHLCV data for charting."""
    end = datetime.now()
    start = end - timedelta(days=365)
    return get_stock_data(symbol, start_date=start, end_date=end)

def compute_indicators(df):
    """Compute EMAs, MACD, RSI on OHLCV DataFrame."""
    df = df.copy()
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

def build_chart(symbol, signal_label):
    raw = fetch_chart_data(symbol)
    if raw is None or raw.empty:
        return None

    df = compute_indicators(raw)
    df = df.tail(180)

    is_buy = "Buy" in signal_label
    signal_icon  = "🟢 BUY"  if is_buy else "🔴 SELL"

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.035, row_heights=[0.58, 0.22, 0.20],
        subplot_titles=(f"{symbol}  {signal_icon}", "MACD", "RSI (14)")
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
            marker=dict(symbol="triangle-up", color="#00C076", size=13),
            name="Buy Signal",
            showlegend=False
        ), row=1, col=1)

    # Plot historical SELL signals
    sell_signals = df[df["Is_Sell"]]
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals["High"] * 1.05,
            mode="markers",
            marker=dict(symbol="triangle-down", color="#FF4B4B", size=13),
            name="Sell Signal",
            showlegend=False
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

# ─────────────────────────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    tickers_input = st.text_area("Enter comma-separated tickers:", value="AAPL, TSLA, NVDA, GOOGL, META, MSFT")

    if st.button("🚀 Analyze Tickers", type="primary"):
        ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        
        if not ticker_list:
            st.warning("Please enter at least one valid ticker.")
        else:
            with st.spinner("Analyzing custom tickers..."):
                df_results = run_screener(ticker_list)
                st.session_state['custom_screener_results'] = df_results
                st.session_state.pop('custom_selected_ticker', None)

with col2:
    if 'custom_screener_results' in st.session_state:
        df = st.session_state['custom_screener_results']
        
        st.success("✅ Scan completed!")
        
        if df.empty:
            st.warning("No data retrieved.")
        else:
            buy_count  = len(df[df['Signal'] == 'Buy'])
            sell_count = len(df[df['Signal'] == 'Sell'])

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Signals", len(df))
            mc2.metric("🟢 Buy Signals",  buy_count)
            mc3.metric("🔴 Sell Signals", sell_count)
            
            st.markdown("##### 📋 Click a ticker to view the chart ↓")
            def styling_logic(val):
                c = '#00C076' if val == 'Buy' else '#FF4B4B' if val == 'Sell' else 'inherit'
                return f'color: {c}; font-weight: bold;'
                
            # Note: Pandas Styler 'applymap' was renamed to 'map' in pandas >= 2.1.0. 
            # Styler.applymap is still available in older versions. We use map if we assume pandas 2.3.3.
            st.dataframe(
                df.style.map(styling_logic, subset=['Signal']).format({"Current Price": "{:.1f}"}),
                use_container_width=True,
                height=280,
                on_select="rerun",
                selection_mode="single-row",
                key="custom_signal_table"
            )
            
            sel = st.session_state.get("custom_signal_table", {})
            sel_rows = sel.get("selection", {}).get("rows", [])
            if sel_rows:
                idx = sel_rows[0]
                row = df.iloc[idx]
                st.session_state['custom_selected_ticker'] = row['Symbol']
                st.session_state['custom_selected_signal'] = row['Signal']
    else:
        st.info("👈 Enter tickers and click **Analyze Tickers** to start.")

# ─────────────────────────────────────────────────────────────────
# CHART SECTION
# ─────────────────────────────────────────────────────────────────
if 'custom_selected_ticker' in st.session_state:
    ticker = st.session_state['custom_selected_ticker']
    signal = st.session_state['custom_selected_signal']
    
    st.divider()
    st.subheader(f"📈 {ticker}  —  {signal} Signal Detail")
    
    with st.spinner(f"Loading chart for {ticker}..."):
        fig = build_chart(ticker, signal)
        
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Could not retrieve chart data for {ticker}.")

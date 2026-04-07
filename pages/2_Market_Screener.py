import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from market_screener import run_screener, SP500_LIST, NASDAQ100_LIST, WATCH_LIST
from data_fetcher import get_stock_data
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Market Screener", page_icon="🎯", layout="wide")

st.title("🎯 Advanced Market Screener")
st.markdown("""
This screener scans 500+ stocks in real-time to identify **Buy / Sell** signals based on a multi-timeframe strategy combining:
`EMA Crossovers (5 & 13) | MACD Baseline Validation | RSI Divergence | 233-Day Trend Slope`
""")

st.info("💡 **Backend Engine**: Powered by a unified API architecture (Yahoo Finance with automated fallback to Finnhub & Alpha Vantage during rate limits).")

# ── SYSTEM HEALTH MONITOR ──────────────────────────────────
with st.expander("🛠️ System Backend Status", expanded=False):
    from sqlalchemy import text
    from data_fetcher import engine
    
    try:
        with engine.connect() as conn:
            # Check DB response
            res = conn.execute(text("SELECT MAX(date) FROM stock_prices"))
            max_date = res.fetchone()[0]
            
            h1, h2, h3 = st.columns(3)
            h1.success("🟢 Supabase: Connected")
            if max_date:
                h2.info(f"📅 Data Sync: {max_date}")
            else:
                h2.warning("📅 Data Sync: No data found")
            h3.write(f"🔗 [View GitHub Actions Logs](https://github.com/weiminchen3030/market-dashboard/actions)")
    except Exception as e:
        st.error(f"🔴 Database Connection Error: {str(e)}")
# ────────────────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_screener_results(list_name):
    if list_name == "S&P 500":
        target = SP500_LIST
    elif list_name == "NASDAQ 100":
        target = NASDAQ100_LIST
    else:
        target = WATCH_LIST
    return run_screener(target)


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
    return df


def build_chart(symbol, signal_label):
    """Build an interactive Plotly chart with candlesticks + EMAs + MACD + RSI."""
    raw = fetch_chart_data(symbol)
    if raw is None or raw.empty:
        return None

    df = compute_indicators(raw)

    # Trim to last 180 trading days for a clean view (≈ 9 months)
    df = df.tail(180)

    is_buy = "Buy" in signal_label
    signal_color = "#00C076" if is_buy else "#FF4B4B"
    signal_icon  = "🟢 BUY"  if is_buy else "🔴 SELL"

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.58, 0.22, 0.20],
        subplot_titles=(
            f"{symbol}  {signal_icon}",
            "MACD",
            "RSI (14)"
        )
    )

    # ── Panel 1: Candlestick ──────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        increasing_line_color="#26A69A",
        decreasing_line_color="#EF5350",
        name="Price",
        showlegend=False,
    ), row=1, col=1)

    ema_colors = {
        "EMA5":   ("#F9A825", 1.2),
        "EMA13":  ("#29B6F6", 1.2),
        "EMA55":  ("#AB47BC", 1.5),
        "EMA233": ("#FF7043", 2.0),
    }
    for ema, (color, width) in ema_colors.items():
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema],
            line=dict(color=color, width=width),
            name=ema, showlegend=True
        ), row=1, col=1)

    # Highlight the signal on the last bar
    last_row = df.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[df.index[-1]],
        y=[last_row["Low"] * 0.975 if is_buy else last_row["High"] * 1.025],
        mode="markers+text",
        marker=dict(
            symbol="triangle-up" if is_buy else "triangle-down",
            color=signal_color, size=14
        ),
        text=[signal_icon],
        textposition="bottom center" if is_buy else "top center",
        textfont=dict(size=11, color=signal_color),
        name="Signal",
        showlegend=False,
    ), row=1, col=1)

    # ── Panel 2: MACD ─────────────────────────────────────────────
    colors_hist = ["#26A69A" if v >= 0 else "#EF5350" for v in df["MACD_Hist"]]
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACD_Hist"],
        marker_color=colors_hist, name="MACD Histogram", showlegend=False
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"],
        line=dict(color="#29B6F6", width=1.2),
        name="MACD", showlegend=False
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Signal_Line"],
        line=dict(color="#FF7043", width=1.2, dash="dot"),
        name="Signal", showlegend=False
    ), row=2, col=1)

    # ── Panel 3: RSI ──────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"],
        line=dict(color="#AB47BC", width=1.5),
        name="RSI", showlegend=False
    ), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="red",   width=1, dash="dot"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="green", width=1, dash="dot"), row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)",
                  line_width=0, row=3, col=1)

    # ── Layout ────────────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=780,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=11)
        ),
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)

    return fig


# ─────────────────────────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    selected_index = st.radio(
        "Select Universe to Scan:",
        ("S&P 500", "NASDAQ 100", "Watchlist"),
        index=0
    )

    if st.button("🚀 Run Live Screener", type="primary"):
        st.session_state['last_scan'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.pop('selected_ticker', None)  # reset chart on new scan

        with st.spinner(f"Scanning {selected_index} universe... This may take up to a minute depending on API limits..."):
            start_time = time.time()
            df_results = fetch_screener_results(selected_index)
            st.session_state['screener_results'] = df_results
            st.session_state['scan_duration'] = round(time.time() - start_time, 1)

with col2:
    if 'screener_results' in st.session_state:
        df = st.session_state['screener_results']

        st.success(f"✅ Scan completed! Evaluated in {st.session_state.get('scan_duration', 0)} seconds.")
        st.caption(f"Last updated: {st.session_state.get('last_scan')} (Results cached for 1 hour)")

        if df.empty:
            st.warning("No Buy or Sell signals detected across the entire universe today.")
        else:
            buy_count  = len(df[df['Signal'] == 'Buy'])
            sell_count = len(df[df['Signal'] == 'Sell'])

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Signals", len(df))
            mc2.metric("🟢 Buy Signals",  buy_count)
            mc3.metric("🔴 Sell Signals", sell_count)

            # ── Interactive signal table ──────────────────────────
            st.markdown("##### 📋 Click a ticker to view the chart ↓")

            def styling_logic(val):
                c = '#00C076' if val == 'Buy' else '#FF4B4B'
                return f'color: {c}; font-weight: bold;'

            st.dataframe(
                df.style.map(styling_logic, subset=['Signal']),
                use_container_width=True,
                height=280,
                on_select="rerun",
                selection_mode="single-row",
                key="signal_table"
            )

            # Detect row selection
            sel = st.session_state.get("signal_table", {})
            sel_rows = sel.get("selection", {}).get("rows", [])
            if sel_rows:
                idx = sel_rows[0]
                row = df.iloc[idx]
                st.session_state['selected_ticker'] = row['Symbol']
                st.session_state['selected_signal'] = row['Signal']

    else:
        st.info("👈 Click **Run Live Screener** to start the analysis across the selected universe.")


# ─────────────────────────────────────────────────────────────────
# CHART SECTION (full width below)
# ─────────────────────────────────────────────────────────────────
if 'selected_ticker' in st.session_state:
    ticker  = st.session_state['selected_ticker']
    signal  = st.session_state['selected_signal']

    st.divider()
    st.subheader(f"📈 {ticker}  —  {signal} Signal Detail")

    with st.spinner(f"Loading chart for {ticker}..."):
        fig = build_chart(ticker, signal)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

        # Quick stats below chart
        raw = fetch_chart_data(ticker)
        if raw is not None and not raw.empty:
            latest = raw.iloc[-1]
            prev   = raw.iloc[-2] if len(raw) > 1 else raw.iloc[-1]
            pct_chg = (latest["Close"] - prev["Close"]) / prev["Close"] * 100

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Close",  f"${latest['Close']:.2f}")
            s2.metric("Change", f"{pct_chg:+.2f}%",
                      delta_color="normal" if pct_chg >= 0 else "inverse")
            s3.metric("High",   f"${latest['High']:.2f}")
            s4.metric("Low",    f"${latest['Low']:.2f}")
    else:
        st.error(f"Could not retrieve chart data for {ticker}.")

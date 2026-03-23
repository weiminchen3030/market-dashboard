import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

from scrapers import (
    get_crypto_fng,
    get_naaim,
    get_vix_data,
    get_td_sequential,
    scrape_with_playwright,
)
import json
import re
from datetime import datetime
st.set_page_config(page_title="Daily Market Intelligence", page_icon="📈", layout="wide")
st.title(f"📈 Daily Market Intelligence — {datetime.today().strftime('%Y-%m-%d')}")
st.markdown("---")


# ── Helpers ────────────────────────────────────────────────────────────────────

def next_trading_days(last_date, n=15):
    result = []
    d = pd.Timestamp(last_date) + pd.Timedelta(days=1)
    while len(result) < n:
        if d.dayofweek < 5:
            result.append(d.strftime('%m/%d'))
        d += pd.Timedelta(days=1)
    return result


def plot_td_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """
    Candlestick with:
    - Trading-day-only x-axis (no weekend gaps) via string category labels
    - MA20 (blue), MA60 (orange), MA120 (red)
    - TD 1-8 and 10-12: small number text above/below candle
    - TD 9 :  ▲ yellow (buy setup) / ▼ red (sell setup)
    - TD 13:  ▲ blue   (buy setup) / ▼ purple (sell setup)
    - 15 future blank trading days as right-side padding
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    labels = df.index.strftime('%m/%d').tolist()
    all_labels = labels + next_trading_days(df.index[-1], n=15)

    fig = go.Figure()

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=labels,
        open=df['Open'], high=df['High'],
        low=df['Low'],   close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
    ))

    # Moving averages
    for ma_col, color in [('MA20', 'cornflowerblue'), ('MA60', 'orange'), ('MA120', 'tomato')]:
        if ma_col in df.columns:
            fig.add_trace(go.Scatter(
                x=labels, y=df[ma_col].values,
                name=ma_col, mode='lines',
                line=dict(color=color, width=1.4),
            ))

    # ── TD annotations ────────────────────────────────────────────────────────
    # Sell setup (TD_Up): "High" — above the candle
    # Buy  setup (TD_Down): "Low" — below the candle

    high_arrow_x,  high_arrow_y,  high_arrow_txt, high_arrow_col = [], [], [], []
    low_arrow_x,   low_arrow_y,   low_arrow_txt,  low_arrow_col  = [], [], [], []

    for i in range(len(df)):
        lbl  = labels[i]
        up   = int(df['TD_Up'].iloc[i])
        down = int(df['TD_Down'].iloc[i])
        high = df['High'].iloc[i]
        low  = df['Low'].iloc[i]

        if up > 0:
            if up == 9:
                # Red downward triangle above candle
                high_arrow_x.append(lbl);   high_arrow_y.append(high * 1.002)
                high_arrow_txt.append('▼'); high_arrow_col.append('#ff2222')
            elif up == 13:
                # Purple downward triangle above candle
                high_arrow_x.append(lbl);   high_arrow_y.append(high * 1.002)
                high_arrow_txt.append('▼'); high_arrow_col.append('#cc44ff')
            else:
                # Small number
                fig.add_annotation(x=lbl, y=high, yanchor='bottom', yshift=4,
                                   text=str(up), showarrow=False,
                                   font=dict(color='#ff6b6b', size=8, family='monospace'))

        if down > 0:
            if down == 9:
                # Yellow upward triangle below candle
                low_arrow_x.append(lbl);   low_arrow_y.append(low * 0.998)
                low_arrow_txt.append('▲'); low_arrow_col.append('#FFD700')
            elif down == 13:
                # Blue upward triangle below candle
                low_arrow_x.append(lbl);   low_arrow_y.append(low * 0.998)
                low_arrow_txt.append('▲'); low_arrow_col.append('#1E90FF')
            else:
                fig.add_annotation(x=lbl, y=low, yanchor='top', yshift=-4,
                                   text=str(down), showarrow=False,
                                   font=dict(color='#4dffb4', size=8, family='monospace'))

    # Batch all arrow markers via Scatter (text mode = emoji triangles)
    # Use separate traces to allow per-point colors via marker.color list
    if high_arrow_x:
        fig.add_trace(go.Scatter(
            x=high_arrow_x, y=high_arrow_y,
            mode='text',
            text=high_arrow_txt,
            textfont=dict(color=high_arrow_col, size=14),
            textposition='top center',
            showlegend=False,
            hovertemplate='TD High<extra></extra>',
        ))

    if low_arrow_x:
        fig.add_trace(go.Scatter(
            x=low_arrow_x, y=low_arrow_y,
            mode='text',
            text=low_arrow_txt,
            textfont=dict(color=low_arrow_col, size=14),
            textposition='bottom center',
            showlegend=False,
            hovertemplate='TD Low<extra></extra>',
        ))

    n_all = len(all_labels)
    # Force xaxis range to include all future blank labels (index 0 … n_all-1)
    # This is necessary with staticPlot=True because Plotly otherwise trims to data extent
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=13)),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=all_labels,
            range=[-0.5, n_all - 0.5],   # ← ensures all future blank slots are visible
            tickangle=-45,
            tickfont=dict(size=7),
            rangeslider=dict(visible=False),
            gridcolor='rgba(255,255,255,0.05)',
            nticks=20,
        ),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        height=430,
        margin=dict(l=0, r=0, t=38, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(18,18,18,1)',
        font=dict(color='white'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig

def get_status_light(indicator: str, val: float):
    if indicator in ("CNN Fear & Greed", "Crypto Fear & Greed"):
        if val <= 25: return "🔴", "Extreme Fear"
        if val <= 45: return "🟠", "Fear"
        if val <= 55: return "🟡", "Neutral"
        if val <= 75: return "🟢", "Greed"
        return "🟢", "Extreme Greed"
    elif indicator == "NAAIM Exposure":
        if val <= 40: return "🔴", "Bearish"
        if val <= 80: return "🟡", "Neutral"
        return "🟢", "Bullish"
    elif indicator == "Trading Logic Breadth":
        if val <= 300: return "🔴", "Oversold"
        if val <= 800: return "🟡", "Neutral"
        return "🟢", "Overbought"
    elif indicator == "AAII Spread":
        if val <= -10: return "🔴", "Pessimism"
        if val <= 10:  return "🟡", "Neutral"
        return "🟢", "Optimism"
    elif indicator == "VIX":
        if val <= 15: return "🟢", "Complacency"
        if val <= 20: return "🟡", "Normal"
        return "🔴", "High Volatility (Fear)"
    return "⚪", "Unknown"

def parse_numeric(val, default=0):
    if val in ("N/A", None, ""):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r'(-?[\d\.]+)', str(val))
    return float(m.group(1)) if m else default

# ── Main UI ────────────────────────────────────────────────────────────────────

if st.button("🔄 Fetch Today's Data", type="primary"):
    prog = st.progress(0, text="Starting…")

    prog.progress(10, text="Fetching NAAIM, Crypto, VIX…")
    naaim      = get_naaim()
    crypto_fng = get_crypto_fng()
    vix_data   = get_vix_data()

    prog.progress(30, text="Fetching options and technical data…")

    prog.progress(50, text="Downloading 1 year of price data & TD Sequential…")
    td_data    = get_td_sequential()

    prog.progress(70, text="Browser scraping Trading Logic / CNN / Truflation / AAII…")
    pw         = scrape_with_playwright()

    prog.progress(100, text="Done!")
    prog.empty()

    # ── Summary Table ─────────────────────────────────────────────────────────
    st.markdown("## 🚦 Market Dashboard Summary")
    
    # Parse values
    cnn_val = parse_numeric(pw.get("CNNFearGreed", 50))
    crypto_val = parse_numeric(crypto_fng)
    n_val = naaim.get("value", 50) if isinstance(naaim, dict) else naaim
    naaim_val = parse_numeric(n_val)
    tl_val = parse_numeric(pw.get("TradingLogic", 500))
    vix_val = parse_numeric(vix_data.get("VIX", 20))
    
    aaii_dict = pw.get("AAII", {})
    aaii_bull = parse_numeric(aaii_dict.get("Bullish"))
    aaii_bear = parse_numeric(aaii_dict.get("Bearish"))
    aaii_spread = aaii_bull - aaii_bear if aaii_bull and aaii_bear else 0

    # Build Summary Data
    summary_data = [
        {"Indicator": "CNN Fear & Greed", "Description": "Stock Market Sentiment (0-100)", "Value": pw.get("CNNFearGreed", "N/A"), "ValNum": cnn_val},
        {"Indicator": "Crypto Fear & Greed", "Description": "Crypto Market Sentiment (0-100)", "Value": crypto_fng, "ValNum": crypto_val},
        {"Indicator": "NAAIM Exposure", "Description": "Active Manager Exposure Index", "Value": n_val, "ValNum": naaim_val},
        {"Indicator": "Trading Logic Breadth", "Description": "Market Breadth Score (0-1100)", "Value": pw.get("TradingLogic", "N/A"), "ValNum": tl_val},
        {"Indicator": "AAII Spread", "Description": "Retail Bull-Bear Spread (%)", "Value": f"{aaii_spread:+.2f}%", "ValNum": aaii_spread},
        {"Indicator": "VIX", "Description": "Volatility Index (Fear Gauge)", "Value": vix_data.get("VIX", "N/A"), "ValNum": vix_val},
    ]

    for item in summary_data:
        light, status = get_status_light(item["Indicator"], item["ValNum"])
        item["Signal"] = f"{light} {status}"

    st.dataframe(
        pd.DataFrame(summary_data).drop(columns=["ValNum"]).set_index("Indicator"), 
        use_container_width=True
    )
    
    st.markdown("---")

    # ── Indicators ────────────────────────────────────────────────────────────
    st.markdown("## 📊 Key Indicators")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🌐 Trading Logic Breadth", pw.get("TradingLogic", "N/A"), help="Score / 1100")
    c2.metric("📋 NAAIM Exposure",
              naaim.get("value", "N/A") if isinstance(naaim, dict) else naaim,
              help=naaim.get("date", "") if isinstance(naaim, dict) else "")
    c3.metric("😨 CNN Fear & Greed",   pw.get("CNNFearGreed", "N/A"))
    c4.metric("₿ Crypto Fear & Greed", crypto_fng)
    c5.metric("📈 Truflation CPI",     pw.get("Truflation",   "N/A"))

    st.markdown("---")

    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("⚡ VIX",        vix_data.get("VIX",      "N/A"))
    r2c2.metric("⚡ VVIX",       vix_data.get("VVIX",     "N/A"))
    r2c3.metric("📐 VIX/VVIX",  vix_data.get("VIX/VVIX", "N/A"))

    # ── AAII ──────────────────────────────────────────────────────────────────
    aaii = pw.get("AAII", {"Bullish": "N/A", "Neutral": "N/A", "Bearish": "N/A"})
    st.markdown("---")
    st.markdown("#### 🐂 AAII Sentiment Survey")
    
    ac1, ac2, ac3 = st.columns(3)
    ac1.metric("Bullish 🟢", aaii.get("Bullish", "N/A"))
    ac2.metric("Neutral ⚪", aaii.get("Neutral", "N/A"))
    ac3.metric("Bearish 🔴", aaii.get("Bearish", "N/A"))

    # ── TD Snapshot table ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🔢 TD Sequential Snapshot")
    rows = []
    for sym, d in td_data.items():
        rows.append({
            "Symbol": sym,
            "Last Close": d.get("Last Close", "N/A"),
            "Current Price": d.get("Current Price", d.get("Price", "N/A")),
            "TD Setup": d["TD"]
        })
    st.dataframe(pd.DataFrame(rows).set_index("Symbol"), use_container_width=True)

    # ── Charts ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📉 Candlestick Charts  *(Trading days only · MA20/60/120 · TD 9-count)*")
    st.caption(
        "🔴▼ = High 9 (Sell Setup)  ·  🟣▼ = High 13  ·  🟡▲ = Low 9 (Buy Setup)  ·  🔵▲ = Low 13"
    )

    symbols_to_plot = ['SPY', 'QQQ', 'DIA', 'IWM', '^VIX']
    valid = [(s, td_data[s]) for s in symbols_to_plot
             if s in td_data and td_data[s]["DF"] is not None]

    left_col, right_col = st.columns(2)
    for idx, (sym, d) in enumerate(valid):
        # Only display last ~3 months (~65 trading days) even though we calculated on 1y
        df_view = d["DF"].iloc[-65:]
        fig = plot_td_chart(df_view, sym)
        (left_col if idx % 2 == 0 else right_col).plotly_chart(
            fig, use_container_width=True, config={"staticPlot": True}
        )

    # ── Data Sources ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🔗 Data Sources")
    st.caption("External links to the original data providers.")
    st.markdown("""
    - **CNN Fear & Greed**: [edition.cnn.com/markets/fear-and-greed](https://edition.cnn.com/markets/fear-and-greed)
    - **Crypto Fear & Greed**: [alternative.me/crypto](https://alternative.me/crypto/fear-and-greed-index/)
    - **NAAIM Exposure Index**: [naaim.org](https://www.naaim.org/programs/naaim-exposure-index/)
    - **Trading Logic Breadth**: [tradinglogic.net](https://tradinglogic.net/)
    - **AAII Sentiment**: [TradingView Bullish](https://www.tradingview.com/symbols/AAII-BULLISH/minds/) · [TradingView Bearish](https://www.tradingview.com/symbols/AAII-BEARISH/minds/)
    - **Truflation US CPI**: [truflation.com](https://truflation.com/)
    - **Price Data & VIX**: Yahoo Finance via `yfinance`
    """)


else:
    st.markdown("""
    ## Welcome  
    Click **🔄 Fetch Today's Data** to collect all market indicators and render interactive charts.

    **TD Sequential legend:**  
    🟡▲ Low 9 (Buy Setup)  ·  🔵▲ Low 13  ·  🔴▼ High 9 (Sell Setup)  ·  🟣▼ High 13  
    Small green numbers = Low 1-8, 10-12  ·  Small red numbers = High 1-8, 10-12
    """)

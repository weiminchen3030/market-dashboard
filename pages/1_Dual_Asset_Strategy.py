import streamlit as st
import pandas as pd
from data_fetcher import get_stock_data

from demark_backtest import calc_ma, calc_demark, calc_rsi, backtest_dca, plot_chart

st.set_page_config(page_title="Dual-Asset State Machine Strategy", page_icon="💎", layout="wide")
st.title("💎 State-Machine Quantitative Backtester")

st.markdown("""
### Strategy Overview
This page simulates a **10-Year dual-asset quantitative strategy**. It employs systematic DCA into a base index (like SPY or QQQ) during multiple bull markets (`MA20 > 60 > 120`). 
When technicals warn of an impending crash (Death Crosses), it liquidates the base asset into cash. 
In pure bear markets, it ignores ordinary dips but deploys ALL cached capital directly into a **3X Leveraged Asset** (like UPRO or TQQQ) upon detecting an extreme capitulation Diamond Pit (`VIX > 30` + technical bottoms), with a strict 10% auto-stop loss.
""")
            
st.markdown("---")

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_and_process_data(ticker, lev_ticker, years=10):
    end_date = pd.Timestamp.now()
    test_start_date = end_date - pd.DateOffset(years=years)
    fetch_start_date = test_start_date - pd.DateOffset(days=200)

    try:
        # Utilize robust fetcher that falls back to Finnhub / Alpha Vantage
        df = get_stock_data(ticker, start_date=fetch_start_date, end_date=end_date)
        vix_df = get_stock_data('^VIX', start_date=fetch_start_date, end_date=end_date)
        lev_df = get_stock_data(lev_ticker, start_date=fetch_start_date, end_date=end_date)
        
        if df is None or df.empty:
            raise ValueError(f"Failed to fetch base ticker {ticker}")
            
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        if isinstance(vix_df.columns, pd.MultiIndex): vix_df.columns = vix_df.columns.droplevel(1)
        if isinstance(lev_df.columns, pd.MultiIndex): lev_df.columns = lev_df.columns.droplevel(1)
            
        df['VIX'] = vix_df['Close'].ffill()
        df['Lev_Open'] = lev_df['Open'].ffill()
        df['Lev_High'] = lev_df['High'].ffill()
        df['Lev_Low'] = lev_df['Low'].ffill()
        df['Lev_Close'] = lev_df['Close'].ffill()
    except Exception as e:
        st.error(f"Failed to fetch data for {ticker}/{lev_ticker}: {e}")
        return None
        
    df = calc_ma(df)
    df = calc_demark(df)
    df = calc_rsi(df)
    df = df[df.index >= test_start_date]
    df.dropna(inplace=True)
    return df

# UI layout
tab_spy, tab_qqq = st.tabs(["🇺🇸 SPY & UPRO", "🚀 QQQ & TQQQ"])

# ─────────────────── SPY / UPRO TAB ───────────────────
with tab_spy:
    with st.spinner("Downloading and processing 10-Year SPY metrics..."):
        df_spy = fetch_and_process_data("SPY", "UPRO", 10)
        
    if df_spy is not None:
        fe, fbe, si, bi, tr, br, history, df_spy_backtested = backtest_dca(df_spy, monthly_injection=500.0)
        
        st.markdown(f"#### 10-Year Simulated Outcomes (Monthly $500)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cash Out of Pocket", f"${si:,.0f}")
        c2.metric("Base DCA Output", f"${fbe:,.0f}", f"+{br*100:.1f}%", delta_color="normal")
        c3.metric("State-Machine Output", f"${fe:,.0f}", f"+{tr*100:.1f}%", delta_color="normal")
        c4.metric("Excess Alpha", f"${fe - fbe:,.0f}")
        
        fig_spy, _ = plot_chart(df_spy_backtested, history, "SPY", "UPRO")
        st.plotly_chart(fig_spy, use_container_width=True)

# ─────────────────── QQQ / TQQQ TAB ───────────────────
with tab_qqq:
    with st.spinner("Downloading and processing 10-Year QQQ metrics..."):
        df_qqq = fetch_and_process_data("QQQ", "TQQQ", 10)
        
    if df_qqq is not None:
        fe2, fbe2, si2, bi2, tr2, br2, history2, df_qqq_backtested = backtest_dca(df_qqq, monthly_injection=500.0)
        
        st.markdown(f"#### 10-Year Simulated Outcomes (Monthly $500)")
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Cash Out of Pocket", f"${si2:,.0f}")
        cc2.metric("Base DCA Output", f"${fbe2:,.0f}", f"+{br2*100:.1f}%", delta_color="normal")
        cc3.metric("State-Machine Output", f"${fe2:,.0f}", f"+{tr2*100:.1f}%", delta_color="normal")
        cc4.metric("Excess Alpha", f"${fe2 - fbe2:,.0f}")
        
        fig_qqq, _ = plot_chart(df_qqq_backtested, history2, "QQQ", "TQQQ")
        st.plotly_chart(fig_qqq, use_container_width=True)

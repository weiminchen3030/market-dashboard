import streamlit as st
import pandas as pd
from market_screener import run_screener, SP500_LIST, NASDAQ100_LIST, WATCH_LIST
from datetime import datetime
import time

st.set_page_config(page_title="Market Screener", page_icon="🎯", layout="wide")

st.title("🎯 Advanced Market Screener")
st.markdown("""
This screener scans 500+ stocks in real-time to identify **Buy / Sell** signals based on a multi-timeframe strategy combining:
`EMA Crossovers (5 & 13) | MACD Baseline Validation | RSI Divergence | 233-Day Trend Slope`
""")

# Note on API fallback
st.info("💡 **Backend Engine**: Powered by a unified API architecture (Yahoo Finance with automated fallback to Finnhub & Alpha Vantage during rate limits).")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_screener_results(list_name):
    # Map to correct list
    if list_name == "S&P 500":
        target = SP500_LIST
    elif list_name == "NASDAQ 100":
        target = NASDAQ100_LIST
    else:
        target = WATCH_LIST

    # Because this is cached, we cannot easily use a live progress bar without breaking Streamlit's hash,
    # so we rely on the custom spinner we provide in the UI wrapper.
    return run_screener(target)


# UI Layout
col1, col2 = st.columns([1, 2])

with col1:
    selected_index = st.radio(
        "Select Universe to Scan:",
        ("S&P 500", "NASDAQ 100", "Watchlist"),
        index=0
    )
    
    if st.button("🚀 Run Live Screener", type="primary"):
        # We store the latest run time in session state perfectly
        st.session_state['last_scan'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
            # Metrics
            buy_count = len(df[df['Signal'] == 'Buy'])
            sell_count = len(df[df['Signal'] == 'Sell'])
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Signals", len(df))
            mc2.metric("🟢 Buy Signals", buy_count)
            mc3.metric("🔴 Sell Signals", sell_count)
            
            # Format display dataframe smartly
            display_df = df.copy()
            
            def styling_logic(val):
                color = '#00FF00' if val == 'Buy' else '#FF4B4B'
                return f'color: {color}; font-weight: bold;'
                
            st.dataframe(
                display_df.style.map(styling_logic, subset=['Signal']),
                use_container_width=True,
                height=600
            )
            
    else:
        st.info("👈 Click **Run Live Screener** to start the analysis across the selected universe.")

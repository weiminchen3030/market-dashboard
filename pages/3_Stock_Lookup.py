import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from market_screener import process_stock, calculate_indicators, apply_strategy

st.set_page_config(page_title="Stock Lookup", page_icon="📈", layout="wide")
st.title("📈 Stock Lookup & Analysis")

st.markdown("""
### Query Specific Stock Data
Enter a stock ticker below to fetch and visualize its recent market data.
""")

col1, col2 = st.columns([1, 2])

with col1:
    ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, MSFT, TSLA):", value="AAPL")
    period = st.selectbox("Select Time Period:", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    fetch_btn = st.button("Fetch Data", type="primary")

if fetch_btn or ticker:
    try:
        with st.spinner(f"Fetching data for {ticker}..."):
            stock = yf.Ticker(ticker)
            
            # Fetch max data to safely calculate EMA233 and others
            full_df = stock.history(period="max")
            
            if not full_df.empty:
                full_df = calculate_indicators(full_df)
                full_df['Signal_Value'] = apply_strategy(full_df, return_series=True)
                
                # Filter down to requested period for viewing
                if period == "max":
                    df = full_df.copy()
                else:
                    # Approximation for slicing
                    period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
                    days = period_days.get(period, 365)
                    start_date = datetime.now() - timedelta(days=days)
                    # Convert to timezone aware if dataframe is timezone aware
                    if full_df.index.tz is not None:
                        start_date = start_date.replace(tzinfo=full_df.index.tz)
                    df = full_df[full_df.index >= start_date].copy()
                
                # The current signal is just the very last row
                last_signal_val = full_df['Signal_Value'].iloc[-1]
                current_signal = "Buy" if last_signal_val == 1 else ("Sell" if last_signal_val == -1 else "Neutral")
            else:
                df = full_df
            
        if df.empty:
            st.error(f"No data found for ticker '{ticker}'. Please check the symbol and try again.")
        else:
            # Display basic info
            info = stock.info
            st.subheader(f"Data for {ticker.upper()}")
            
            # Show Signal prominently
            signal_color = "#00C076" if current_signal == "Buy" else ("#FF4B4B" if current_signal == "Sell" else "#888888")
            signal_icon = "🟢" if current_signal == "Buy" else ("🔴" if current_signal == "Sell" else "⚪")
            st.markdown(f"### Current Technical Signal: <span style='color:{signal_color}'>{signal_icon} {current_signal.upper()}</span>", unsafe_allow_html=True)
            
            if 'shortName' in info:
                st.write(f"**Company:** {info.get('shortName', '')} | **Sector:** {info.get('sector', 'N/A')} | **Industry:** {info.get('industry', 'N/A')}")
            
            # Current price metrics
            last_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else last_close
            pct_change = ((last_close - prev_close) / prev_close) * 100
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Last Close", f"${last_close:.2f}", f"{pct_change:.2f}%")
            mc2.metric("Volume", f"{int(df['Volume'].iloc[-1]):,}")
            mc3.metric("52 Week High", f"${info.get('fiftyTwoWeekHigh', df['High'].max()):.2f}")

            # Plot candlestick chart
            fig = go.Figure()
            
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name=ticker))
                            
            # Add Buy/Sell Signals to Chart
            buy_signals = df[df['Signal_Value'] == 1]
            sell_signals = df[df['Signal_Value'] == -1]
            
            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['Low'] * 0.95,
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=15, color='#00C076', line=dict(width=2, color='DarkSlateGrey')),
                    name='Buy Signal'
                ))
                
            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['High'] * 1.05,
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=15, color='#FF4B4B', line=dict(width=2, color='DarkSlateGrey')),
                    name='Sell Signal'
                ))
                            
            fig.update_layout(
                title=f"{ticker.upper()} Price Action",
                yaxis_title='Price (USD)',
                xaxis_title='Date',
                template='plotly_dark' if st.get_option('theme.base') == 'dark' else 'plotly_white',
                height=600,
                margin=dict(l=0, r=0, t=40, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show historical signals table (Past 1 Year)
            st.markdown("### 📋 Recent Signals (Past 1 Year)")
            one_year_ago = datetime.now() - timedelta(days=365)
            if full_df.index.tz is not None:
                one_year_ago = one_year_ago.replace(tzinfo=full_df.index.tz)
            
            recent_signals = full_df[(full_df.index >= one_year_ago) & (full_df['Signal_Value'] != 0)].copy()
            if recent_signals.empty:
                st.info("No Buy or Sell signals triggered in the past year.")
            else:
                recent_signals['Signal Type'] = recent_signals['Signal_Value'].map({1: "🟢 BUY", -1: "🔴 SELL"})
                recent_signals['Date'] = recent_signals.index.strftime('%Y-%m-%d')
                display_df = recent_signals[['Date', 'Signal Type', 'Close', 'Volume']].sort_index(ascending=False).reset_index(drop=True)
                
                # Format Close to 2 decimal places
                display_df['Close'] = display_df['Close'].apply(lambda x: f"${x:.2f}")
                
                st.dataframe(display_df, use_container_width=True)
            
            with st.expander("View Raw Data"):
                # Reset index to make Date a column for better display
                df_display = df.reset_index().sort_values('Date', ascending=False)
                st.dataframe(df_display.head(50), use_container_width=True)
                
    except Exception as e:
        st.error(f"An error occurred while fetching data: {e}")

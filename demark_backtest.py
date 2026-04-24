import yfinance as yf
import pandas as pd
import numpy as np
import argparse
import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calc_rsi(df, period=14):
    delta = df['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.ewm(com=period-1, adjust=False).mean()
    roll_down = down.ewm(com=period-1, adjust=False).mean()
    rs = roll_up / roll_down
    df['RSI'] = 100.0 - (100.0 / (1.0 + rs))
    return df

def calc_ma(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA120'] = df['Close'].rolling(window=120).mean()
    return df

def calc_demark(df):
    df = df.copy()
    df['Buy_9_Signal'] = False
    df['Sell_9_Signal'] = False
    df['Buy_13_Signal'] = False
    df['Sell_13_Signal'] = False

    buy_count = 0
    sell_count = 0
    for i in range(4, len(df)):
        if df['Close'].iloc[i] < df['Close'].iloc[i-4]: buy_count += 1
        else: buy_count = 0
        if df['Close'].iloc[i] > df['Close'].iloc[i-4]: sell_count += 1
        else: sell_count = 0
        
        if buy_count == 9: df.loc[df.index[i], 'Buy_9_Signal'] = True
        if sell_count == 9: df.loc[df.index[i], 'Sell_9_Signal'] = True
            
    active_buy_countdown = False
    active_sell_countdown = False
    buy_cd_count = 0
    sell_cd_count = 0
    
    for i in range(4, len(df)):
        if df['Buy_9_Signal'].iloc[i]:
            active_buy_countdown = True
            buy_cd_count = 0
            active_sell_countdown = False
        if df['Sell_9_Signal'].iloc[i]:
            active_sell_countdown = True
            sell_cd_count = 0
            active_buy_countdown = False
            
        if active_buy_countdown and i >= 2:
            if df['Close'].iloc[i] <= df['Low'].iloc[i-2]:
                buy_cd_count += 1
                if buy_cd_count == 13:
                    df.loc[df.index[i], 'Buy_13_Signal'] = True
                    active_buy_countdown = False
        if active_sell_countdown and i >= 2:
            if df['Close'].iloc[i] >= df['High'].iloc[i-2]:
                sell_cd_count += 1
                if sell_cd_count == 13:
                    df.loc[df.index[i], 'Sell_13_Signal'] = True
                    active_sell_countdown = False

    return df

def backtest_dca(df, monthly_injection=500.0):
    cash = 0.0
    strat_invested = 0.0
    base_invested = 0.0
    baseline_shares = 0.0
    
    spy_shares = 0.0
    spy_cost_basis = 0.0
    
    lev_shares = 0.0
    lev_cost_basis = 0.0
    
    was_bull = False
    was_bear = False
    was_warning = False
    
    trade_history = []
    equity_curve = []
    baseline_equity_curve = []
    invested_curve = []
    cash_curve = []
    
    previous_month = -1
    
    def log_trade(signal, inv_amount, price, lev_p_current):
        spy_pnl = ((price / spy_cost_basis) - 1) * 100 if spy_cost_basis > 0 else 0.0
        lev_pnl = ((lev_p_current / lev_cost_basis) - 1) * 100 if lev_cost_basis > 0 else 0.0
        trade_history.append({
            'Date': current_date,
            'Signal': signal,
            'Price': price,
            'Lev_Price': lev_p_current,
            'Invested_Amount': inv_amount,
            'Cash_Balance': cash,
            'SPY_Cost': spy_cost_basis,
            'SPY_PnL': spy_pnl,
            'SPY_Value': spy_shares * price,
            'Lev_Cost': lev_cost_basis,
            'Lev_PnL': lev_pnl,
            'Lev_Value': lev_shares * lev_p_current
        })
    
    for i in range(len(df)):
        current_date = df.index[i]
        close_price = df['Close'].iloc[i]
        lev_price = df['Lev_Close'].iloc[i]
        
        is_bull = (df['MA20'].iloc[i] > df['MA60'].iloc[i]) and (df['MA60'].iloc[i] > df['MA120'].iloc[i])
        is_bear = (df['MA20'].iloc[i] < df['MA60'].iloc[i]) and (df['MA60'].iloc[i] < df['MA120'].iloc[i])
        is_warning = (df['MA20'].iloc[i] < df['MA60'].iloc[i])
        
        # 1. STOP LOSS FOR LEVERAGE
        if lev_shares > 0:
            lev_return = (lev_price - lev_cost_basis) / lev_cost_basis
            if lev_return <= -0.10:
                revenue = lev_shares * lev_price
                cash += revenue
                lev_shares = 0.0
                lev_cost_basis = 0.0
                log_trade("Lev Stop Loss", -revenue, close_price, lev_price)

        # 2. STATE MACHINE: TRANSITION TO MULTI-BULL
        if is_bull and not was_bull:
            if cash > 0:
                amount_to_invest = cash
                bought_shares = amount_to_invest / close_price
                total_cost = (spy_shares * spy_cost_basis) + amount_to_invest
                spy_shares += bought_shares
                spy_cost_basis = total_cost / spy_shares if spy_shares > 0 else 0
                cash = 0.0
                log_trade('Base Bull Re-entry', amount_to_invest, close_price, lev_price)

        # 3. STATE MACHINE: TRANSITION TO WARNING (SELL 50%)
        if is_warning and not was_warning:
            if spy_shares > 0:
                sold_spy = spy_shares * 0.5
                rev = sold_spy * close_price
                cash += rev
                spy_shares -= sold_spy
                if spy_shares <= 0.0001: spy_cost_basis = 0.0
                log_trade('Base Warning Sell 50%', -rev, close_price, lev_price)
            if lev_shares > 0:
                sold_lev = lev_shares * 0.5
                rev = sold_lev * lev_price
                cash += rev
                lev_shares -= sold_lev
                if lev_shares <= 0.0001: lev_cost_basis = 0.0
                log_trade('Lev Warning Sell 50%', -rev, close_price, lev_price)

        # 4. STATE MACHINE: TRANSITION TO BEAR (LIQUIDATE)
        if is_bear and not was_bear:
            if spy_shares > 0:
                rev = spy_shares * close_price
                cash += rev
                spy_shares = 0.0
                spy_cost_basis = 0.0
                log_trade('Base Bear Liquidate', -rev, close_price, lev_price)
            if lev_shares > 0:
                rev = lev_shares * lev_price
                cash += rev
                lev_shares = 0.0
                lev_cost_basis = 0.0
                log_trade('Lev Bear Liquidate', -rev, close_price, lev_price)

        # 5. MONTHLY DCA INJECTION
        if current_date.month != previous_month:
            base_invested += monthly_injection
            baseline_shares += monthly_injection / close_price
            
            cash += monthly_injection
            strat_invested += monthly_injection
            previous_month = current_date.month
            
            if is_bull and cash > 0:
                amount_to_invest = cash
                bought_shares = amount_to_invest / close_price
                total_cost = (spy_shares * spy_cost_basis) + amount_to_invest
                spy_shares += bought_shares
                spy_cost_basis = total_cost / spy_shares if spy_shares > 0 else 0
                cash = 0.0
                log_trade('Base Bull DCA', amount_to_invest, close_price, lev_price)
                
        # 6. DIP BUYING LOGIC
        vix_panic = df['VIX'].iloc[i] > 30.0
        is_extreme = df['Buy_13_Signal'].iloc[i] and df['RSI'].iloc[i] < 30.0
        is_moderate = df['Buy_9_Signal'].iloc[i] or df['RSI'].iloc[i] < 30.0
        
        dip_triggered = False
        if is_extreme or is_moderate:
            dip_triggered = True
            
        if dip_triggered and cash > 0:
            if vix_panic:
                amount_to_invest = cash 
                bought_lev_shares = amount_to_invest / lev_price
                total_cost = (lev_shares * lev_cost_basis) + amount_to_invest
                lev_shares += bought_lev_shares
                lev_cost_basis = total_cost / lev_shares if lev_shares > 0 else 0
                cash = 0.0
                log_trade("Lev VIX Diamond", amount_to_invest, close_price, lev_price)
            # No SPY dip buys during bear to preserve ammo
        
        was_bull = is_bull
        was_bear = is_bear
        was_warning = is_warning
            
        current_equity = cash + (spy_shares * close_price) + (lev_shares * lev_price)
        baseline_equity = baseline_shares * close_price
        
        equity_curve.append(current_equity)
        baseline_equity_curve.append(baseline_equity)
        invested_curve.append(strat_invested)
        cash_curve.append(cash)
        
    df['Equity'] = equity_curve
    df['Baseline_Equity'] = baseline_equity_curve
    df['Total_Invested'] = invested_curve
    df['Cash_Balance_Curve'] = cash_curve
    
    final_equity = df['Equity'].iloc[-1]
    final_baseline_equity = df['Baseline_Equity'].iloc[-1]
    
    total_return = (final_equity - strat_invested) / strat_invested if strat_invested > 0 else 0
    baseline_return = (final_baseline_equity - base_invested) / base_invested if base_invested > 0 else 0
    
    return final_equity, final_baseline_equity, strat_invested, base_invested, total_return, baseline_return, trade_history, df

def plot_chart(df, trade_history, ticker, lev_ticker):
    fig = make_subplots(rows=3, cols=2, shared_xaxes=True, 
                        vertical_spacing=0.04, horizontal_spacing=0.03,
                        column_widths=[0.55, 0.45],
                        row_heights=[0.45, 0.25, 0.30],
                        specs=[
                            [{"type": "xy"}, {"type": "table", "rowspan": 3}],
                            [{"type": "xy"}, None],
                            [{"type": "xy"}, None]
                        ],
                        subplot_titles=(f'{ticker} Candlestick & DCA Strategy Trades', 'Trade Analytics', '^VIX & Panic Diamonds', '', f'Equity & Cash Balance', ''))
                        
    # ROW 1: SPY (BASE)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=f'{ticker} Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='MA20', line=dict(color='#FFD700', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='MA60', line=dict(color='#ff9900', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], mode='lines', name='MA120', line=dict(color='#ff3300', width=1)), row=1, col=1)
                
    if trade_history:
        exec_df = pd.DataFrame(trade_history)
        
        for name, group in exec_df.groupby('Signal'):
            # BASE ASSET MARKERS (on Row 1)
            if 'Base Bull' in name:
                marker = dict(symbol='circle', size=7, color='cyan', line=dict(width=1, color='white'))
                if 'Re-entry' in name: marker = dict(symbol='star', size=16, color='gold', line=dict(width=1, color='white'))
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 0.98, mode='markers', marker=marker, name=name), row=1, col=1)
            elif 'Base Warning' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 1.05, mode='markers', marker=dict(symbol='triangle-down', size=11, color='pink'), name=name), row=1, col=1)
            elif 'Base Bear' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 1.08, mode='markers', marker=dict(symbol='triangle-down', size=15, color='red', line=dict(width=1)), name=name), row=1, col=1)
            
            # LEVERAGE ASSET MARKERS (on Row 1, using Price as base anchor)
            elif 'Lev VIX Diamond' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 0.88, mode='markers', marker=dict(symbol='diamond', size=18, color='yellow', line=dict(width=2, color='red')), name=name), row=1, col=1)
            elif 'Lev Stop Loss' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 1.10, mode='markers', marker=dict(symbol='x', size=14, color='orange', line=dict(width=3)), name=name), row=1, col=1)
            elif 'Lev Warning' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 1.06, mode='markers', marker=dict(symbol='hexagon', size=11, color='orange', line=dict(width=1)), name=name), row=1, col=1)
            elif 'Lev Bear' in name:
                fig.add_trace(go.Scatter(x=group['Date'], y=group['Price'] * 1.10, mode='markers', marker=dict(symbol='hexagon', size=15, color='darkorange', line=dict(width=2, color='white')), name=name), row=1, col=1)
                    
        # TABLE GENERATION
        exec_df['Date_Str'] = exec_df['Date'].dt.strftime('%y-%m-%d')
        exec_df['Tx'] = exec_df['Invested_Amount'].apply(lambda x: f"${x:,.0f}")
        exec_df['Cash'] = exec_df['Cash_Balance'].apply(lambda x: f"${x:,.0f}")
        
        exec_df['Base_C'] = exec_df['SPY_Cost'].apply(lambda x: f"${x:.0f}" if x>0 else "-")
        exec_df['Base_V'] = exec_df['SPY_Value'].apply(lambda x: f"${x:,.0f}" if x>0 else "")
        exec_df['Base_%'] = exec_df['SPY_PnL'].apply(lambda x: f"{x:+.1f}%" if x!=0 else "")
        exec_df['Base_State'] = exec_df.apply(lambda r: f"{r['Base_V']} ({r['Base_%']})" if r['Base_V'] != "" else "-", axis=1)
        
        exec_df['Lev_C'] = exec_df['Lev_Cost'].apply(lambda x: f"${x:.0f}" if x>0 else "-")
        exec_df['Lev_V'] = exec_df['Lev_Value'].apply(lambda x: f"${x:,.0f}" if x>0 else "")
        exec_df['Lev_%'] = exec_df['Lev_PnL'].apply(lambda x: f"{x:+.1f}%" if x!=0 else "")
        exec_df['Lev_State'] = exec_df.apply(lambda r: f"{r['Lev_V']} ({r['Lev_%']})" if r['Lev_V'] != "" else "-", axis=1)
        
        exec_df = exec_df.sort_values(by='Date', ascending=False)
        
        table_trace = go.Table(
            header=dict(values=['Date', 'Action', 'Tx $', 'Cash', 'B_Cost', 'B_Val(%PnL)', 'L_Cost', 'L_Val(%PnL)'],
                        fill_color='darkslategray', font=dict(color='white', size=11), align='left'),
            cells=dict(values=[exec_df['Date_Str'], exec_df['Signal'].str.replace('Base ','').str.replace('Lev ','(L)'), 
                               exec_df['Tx'], exec_df['Cash'], 
                               exec_df['Base_C'], exec_df['Base_State'], 
                               exec_df['Lev_C'], exec_df['Lev_State']],
                       fill_color='dimgray', font=dict(color='white', size=10), align='left')
        )
        fig.add_trace(table_trace, row=1, col=2)
                
    # ROW 2: VIX
    fig.add_trace(go.Scatter(x=df.index, y=df['VIX'], mode='lines', name='^VIX', line=dict(color='violet', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=[30]*len(df), mode='lines', name='Panic 30', line=dict(color='red', dash='dash')), row=2, col=1)
    
    # ROW 3: EQUITY CURVES
    fig.add_trace(go.Scatter(x=df.index, y=df['Equity'], mode='lines', name='State Machine DCA', line=dict(color='orange', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Baseline_Equity'], mode='lines', name='Vanilla DCA', line=dict(color='cyan', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Cash_Balance_Curve'], mode='lines', name='Cash Balance', line=dict(color='lightgreen', width=1, dash='solid')), row=3, col=1)
    
    dt_all = pd.date_range(start=df.index.min(), end=df.index.max())
    dt_missing = [d.strftime("%Y-%m-%d") for d in dt_all.difference(df.index)]

    fig.update_layout(title=f"Trend DCA: {ticker} vs {lev_ticker}", template='plotly_dark', height=1000)
    fig.update_xaxes(rangebreaks=[dict(values=dt_missing)], rangeslider_visible=False)
    fig.update_xaxes(showline=True, linewidth=1, linecolor='gray', gridcolor='rgba(255, 255, 255, 0.1)')
    
    html_filename = f"demark_chart_{ticker}.html"
    fig.write_html(html_filename)
    return fig, html_filename

def main():
    parser = argparse.ArgumentParser(description="Trend State-Machine Backtester")
    parser.add_argument("--ticker", type=str, required=True)
    parser.add_argument("--lev_ticker", type=str, default="UPRO")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--monthly", type=float, default=500.0)
    args = parser.parse_args()
    
    end_date = pd.Timestamp.now()
    test_start_date = end_date - pd.DateOffset(years=args.years)
    fetch_start_date = test_start_date - pd.DateOffset(days=200)
    
    print(f"Downloading data for {args.ticker}, {args.lev_ticker}, and ^VIX from {fetch_start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    
    try:
        df = yf.download(args.ticker, start=fetch_start_date, end=end_date, progress=False)
        vix_df = yf.download('^VIX', start=fetch_start_date, end=end_date, progress=False)
        lev_df = yf.download(args.lev_ticker, start=fetch_start_date, end=end_date, progress=False)
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        if isinstance(vix_df.columns, pd.MultiIndex): vix_df.columns = vix_df.columns.droplevel(1)
        if isinstance(lev_df.columns, pd.MultiIndex): lev_df.columns = lev_df.columns.droplevel(1)
            
        df['VIX'] = vix_df['Close'].ffill()
        df['Lev_Open'] = lev_df['Open'].ffill()
        df['Lev_High'] = lev_df['High'].ffill()
        df['Lev_Low'] = lev_df['Low'].ffill()
        df['Lev_Close'] = lev_df['Close'].ffill()
    except Exception as e:
        sys.exit(1)
        
    df = calc_ma(df); df = calc_demark(df); df = calc_rsi(df)
    df = df[df.index >= test_start_date]
    
    final_eq, final_base_eq, strat_inv, base_inv, tot_ret, base_ret, history, df = backtest_dca(df, monthly_injection=args.monthly)
    fig, html_file = plot_chart(df, history, args.ticker, args.lev_ticker)
    print(f"\nSaved to: {html_file}")
    
if __name__ == "__main__":
    main()

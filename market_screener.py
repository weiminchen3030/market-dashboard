import pandas as pd
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from data_fetcher import get_stock_data
import time

logger = logging.getLogger(__name__)

# Extracted from user's Discord bot
SP500_LIST = ['AAPL', 'NVDA', 'MSFT', 'AMZN', 'META', 'TSLA', 'GOOGL', 'AVGO', 'GOOG', 'BRK.B', 'JPM', 'LLY', 'V', 'XOM', 'UNH', 'MA', 'COST', 'WMT', 'PG', 'HD', 'NFLX', 'JNJ', 'CRM', 'ABBV', 'BAC', 'ORCL', 'MRK', 'KO', 'CVX', 'WFC', 'CSCO', 'ACN', 'NOW', 'MCD', 'PEP', 'IBM', 'DIS', 'LIN', 'TMO', 'ABT', 'ADBE', 'AMD', 'PM', 'ISRG', 'GE', 'INTU', 'GS', 'CAT', 'TXN', 'QCOM', 'VZ', 'BKNG', 'AXP', 'PLTR', 'T', 'SPGI', 'RTX', 'MS', 'BLK', 'PFE', 'HON', 'NEE', 'DHR', 'CMCSA', 'AMGN', 'PGR', 'LOW', 'TJX', 'UNP', 'AMAT', 'ETN', 'BA', 'BSX', 'C', 'UBER', 'SYK', 'BX', 'COP', 'PANW', 'ADP', 'FI', 'ANET', 'BMY', 'GILD', 'SCHW', 'DE', 'TMUS', 'ADI', 'MMC', 'MDT', 'LMT', 'CB', 'VRTX', 'MU', 'SBUX', 'KKR', 'PLD', 'GEV', 'LRCX', 'UPS', 'NKE', 'MO', 'SO', 'EQIX', 'PYPL', 'ICE', 'CME', 'AMT', 'APH', 'TT', 'ELV', 'CRWD', 'CMG', 'KLAC', 'INTC', 'DUK', 'PH', 'CDNS', 'SHW', 'MDLZ', 'MSI', 'AON', 'CI', 'PNC', 'APO', 'SNPS', 'CL', 'WM', 'USB', 'ZTS', 'REGN', 'WELL', 'MCK', 'MCO', 'TDG', 'CEG', 'EMR', 'MMM', 'ORLY', 'ITW', 'COF', 'GD', 'EOG', 'BDX', 'APD', 'MAR', 'WMB', 'NOC', 'ADSK', 'CTAS', 'AJG', 'FDX', 'FTNT', 'CSX', 'HLT', 'TGT', 'ECL', 'RCL', 'OKE', 'WDAY', 'ABNB', 'TFC', 'CARR', 'GM', 'BK', 'ROP', 'FCX', 'CVS', 'DLR', 'HCA', 'PCAR', 'AZO', 'SRE', 'TRV', 'JCI', 'NXPI', 'NSC', 'SPG', 'SLB', 'KMI', 'AMP', 'AFL', 'ALL', 'CPRT', 'FICO', 'ROST', 'AEP', 'PWR', 'GWW', 'CMI', 'VST', 'URI', 'MSCI', 'MET', 'PSA', 'O', 'AXON', 'PSX', 'AIG', 'D', 'HWM', 'PAYX', 'EW', 'FIS', 'KMB', 'NEM', 'DFS', 'PCG', 'TEL', 'MPC', 'FAST', 'LULU', 'AME', 'PEG', 'PRU', 'KVUE', 'RSG', 'KR', 'DHI', 'LHX', 'BKR', 'COR', 'CTVA', 'CCI', 'CTSH', 'VRSK', 'DAL', 'CBRE', 'XEL', 'A', 'F', 'TRGP', 'IT', 'SYY', 'VLO', 'OTIS', 'IR', 'EXC', 'YUM', 'GLW', 'KDP', 'MNST', 'GEHC', 'DELL', 'STZ', 'HES', 'GIS', 'EA', 'RMD', 'VMC', 'ACGL', 'ODFL', 'IQV', 'CHTR', 'IDXX', 'WAB', 'LEN', 'ROK', 'MLM', 'DD', 'ETR', 'NDAQ', 'GRMN', 'EFX', 'DECK', 'UAL', 'WTW', 'OXY', 'HPQ', 'HIG', 'AVB', 'MTB', 'DXCM', 'ED', 'EXR', 'EBAY', 'IRM', 'EIX', 'VICI', 'CNC', 'WEC', 'MCHP', 'HUM', 'TTWO', 'ANSS', 'CSGP', 'FANG', 'MPWR', 'GDDY', 'TSCO', 'FITB', 'STT', 'CAH', 'GPN', 'XYL', 'RJF', 'KEYS', 'HPE', 'DOW', 'ON', 'PPG', 'CCL', 'NUE', 'KHC', 'BR', 'SW', 'CHD', 'DOV', 'MTD', 'TYL', 'FTV', 'TROW', 'VLTO', 'EQT', 'SYF', 'NVR', 'HSY', 'DTE', 'VTR', 'AWK', 'BRO', 'EQR', 'NTAP', 'ADM', 'WST', 'CPAY', 'PPL', 'WBD', 'AEE', 'HBAN', 'CDW', 'HUBB', 'HAL', 'EXPE', 'PHM', 'CINF', 'PTC', 'DRI', 'SBAC', 'IFF', 'WAT', 'TDY', 'ATO', 'K', 'RF', 'BIIB', 'TPL', 'ZBH', 'CNP', 'LYV', 'ES', 'WDC', 'TER', 'STE', 'FE', 'CLX', 'PKG', 'NTRS', 'ZBRA', 'ULTA', 'DVN', 'LII', 'CBOE', 'LUV', 'WY', 'MKC', 'CMS', 'FSLR', 'LDOS', 'CFG', 'LH', 'LYB', 'IP', 'PODD', 'COO', 'STX', 'FDS', 'NRG', 'INVH', 'ESS', 'LVS', 'SNA', 'MAA', 'WRB', 'TRMB', 'CTRA', 'EL', 'OMC', 'BLDR', 'DGX', 'KEY', 'NI', 'J', 'MOH', 'PNR', 'DG', 'BBY', 'HOLX', 'BALL', 'TSN', 'VRSN', 'STLD', 'JBL', 'PFG', 'IEX', 'GPC', 'MAS', 'SMCI', 'KIM', 'EXPD', 'ARE', 'EG', 'LNT', 'AVY', 'GEN', 'BAX', 'L', 'VTRS', 'TPR', 'ALGN', 'CF', 'DLTR', 'DPZ', 'FFIV', 'AKAM', 'TXT', 'SWKS', 'EVRG', 'EPAM', 'DOC', 'APTV', 'RVTY', 'AMCR', 'JBHT', 'MRNA', 'POOL', 'ROL', 'UDR', 'KMX', 'CAG', 'JKHY', 'HST', 'SWK', 'JNPR', 'CPT', 'CHRW', 'REG', 'NCLH', 'DAY', 'SJM', 'TECH', 'ALLE', 'NDSN', 'BG', 'INCY', 'FOXA', 'AIZ', 'BXP', 'IPG', 'EMN', 'UHS', 'NWSA', 'ALB', 'ERIE', 'TAP', 'PAYC', 'PNW', 'ENPH', 'LKQ', 'CRL', 'GNRC', 'AES', 'RL', 'SOLV', 'HRL', 'GL', 'LW', 'HSIC', 'MKTX', 'MTCH', 'FRT', 'TFX', 'WYNN', 'AOS', 'CPB', 'IVZ', 'APA', 'MGM', 'MOS', 'HAS', 'BF.B', 'HII', 'CE', 'CZR', 'BWA', 'WBA', 'DVA', 'PARA', 'BEN', 'FMC', 'MHK', 'FOX', 'NWS']
NASDAQ100_LIST = ['QQQ', 'AAPL', 'MSFT', 'AMZN', 'NVDA', 'META', 'GOOGL', 'GOOG', 'TSLA', 'AVGO', 'COST', 'ADBE', 'NFLX', 'CSCO', 'PEP', 'TMUS', 'CMCSA', 'AMD', 'INTC', 'INTU', 'TXN', 'QCOM', 'AMGN', 'HON', 'AMAT', 'ISRG', 'SBUX', 'BKNG', 'ADP', 'GILD', 'MDLZ', 'ADI', 'PYPL', 'VRTX', 'REGN', 'LRCX', 'MU', 'FISV', 'KLAC', 'MELI', 'ATVI', 'ASML', 'MNST', 'PANW', 'SNPS', 'CDNS', 'CHTR', 'MAR', 'ORLY', 'CTAS', 'FTNT', 'MRVL', 'ABNB', 'ADSK', 'AEP', 'ALGN', 'ANSS', 'BIIB', 'CPRT', 'CRWD', 'CSX', 'CTSH', 'DDOG', 'DLTR', 'DXCM', 'EA', 'EBAY', 'EXC', 'FAST', 'GFS', 'IDXX', 'ILMN', 'KDP', 'KHC', 'LCID', 'LULU', 'MRNA', 'MTCH', 'NTES', 'NXPI', 'ODFL', 'PCAR', 'PDD', 'ROST', 'SGEN', 'SIRI', 'SPLK', 'SWKS', 'TEAM', 'VRSK', 'WDAY', 'WBA', 'WYNN', 'XEL', 'ZM', 'ZS', 'RIVN', 'CEG', 'DASH', 'ENPH', 'FANG', 'GEHC', 'ON', 'TTD', 'WBD']
WATCH_LIST = ['AI', 'S', 'SOUN', 'INOD', 'PHUN', 'VS', 'POET', 'APLD', 'LASE', 'RR', 'SERV', 'UPWK', 'PRCT', 'PEGA', 'SPY', 'QQQ', 'DIA', 'IWM', 'VXX', 'UVXY', 'SVIX', 'AAPL', 'TSLA', 'NFLX', 'GOOGL', 'AMZN', 'META', 'MSFT', 'XLU', 'XLC', 'XBI', 'XLP', 'XLK', 'XLV', 'IYR', 'XLRE', 'XLB', 'IBB', 'XLY', 'XLE', 'RSP', 'IGV', 'XLF', 'JETS', 'XLI', 'IYT', 'XME', 'SOXX', 'AMD', 'NVDA', 'TSM', 'UNG', 'IEI', 'HYG', 'TLT', 'NVO', 'LLY', 'MRK', 'PFE', 'JNJ', 'AZN', 'NVCR', 'SBUX', 'MCD', 'TGT', 'F', 'PEP', 'NKE', 'OIH', 'DHI', 'FDX', 'CAT', 'BX', 'RIVN', 'AMC', 'AFRM', 'LAZR', 'ARKK', 'CCL', 'GME', 'KRE', 'ENPH', 'CVNA', 'COIN', 'TLT', 'WBA', 'IBM', 'T', 'MMM', 'JNK', 'O', 'JEPI', 'LQD', 'CVX', 'XYLD', 'QYLD', 'EMB', 'UPS', 'XOM', 'INTC', 'JPM', 'AVGO', 'PLTR', 'UBER', 'SLV', 'NIO', 'KWEB', 'EDIT', 'GDX', 'AI', 'UPST', 'GLD', 'US30Y', 'TAN', 'VNQ', 'VZ', 'SOFI', 'PANW', 'PLUG', 'CARR', 'TOL', 'LCID', 'ENTG', 'HOOD', 'SLG', 'DKNG', 'LC', 'SMCI', 'MU', 'SOUN', 'CHWY', 'BILI', 'PDD', 'BHVN', 'RXRX', 'RIOT', 'MARA', 'SNOW', 'XPEV', 'SE', 'PCVX', 'SHOP', 'LVMHF', 'CYTK', 'MDGL', 'GILD', 'EWV', 'ALNY', 'SRPT', 'FROG', 'VKTX', 'LUV', 'UNH', 'ZM', 'KO', 'FXI', 'PRME', 'FXY', 'ORCL', 'BA', 'EBAY', 'REGN', 'PINS', 'RCL', 'DIS', 'COST', 'WMT', 'ARDX', 'ZS', 'PVH', 'LMT', 'IQV', 'CRM', 'CRWD', 'SCHD', 'YCS', 'VRTX', 'PRGO', 'X', 'MRNA', 'TXG', 'BIIB', 'UAL', 'UA', 'AMGN', 'AAL', 'MRVL', 'APO', 'CYBR', 'ARM', 'ITB', 'TTD', 'LULU', 'CRSP', 'MTD', 'HD', 'IOVA', 'KKR', 'SYM', 'ILMN', 'MSTR', 'LRCX', 'KBE', 'NEE', 'UMC', 'XIACY', 'BE', 'D', 'CEG', 'VST', 'CMG', 'DELL', 'QCOM', 'SMH', 'QQQE', 'TONUSDT', 'ABNB', 'MCHP', 'AEP', 'KDP', 'TQQQ', 'SQQQ']

def calculate_indicators(data):
    # EMAs
    data["EMA5"] = data["Close"].ewm(span=5, adjust=False).mean()
    data["EMA13"] = data["Close"].ewm(span=13, adjust=False).mean()
    data["EMA55"] = data["Close"].ewm(span=55, adjust=False).mean()
    data["EMA233"] = data["Close"].ewm(span=233, adjust=False).mean()

    # MACD
    data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["EMA26"] = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["Signal_Line"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"] = data["MACD"] - data["Signal_Line"]

    # RSI
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # Price trend
    data["HighLevel"] = data["High"].rolling(window=15).max()
    data["LowLevel"] = data["Low"].rolling(window=15).min()

    # EMA233 slope
    data["EMA233_Slope"] = data["EMA233"].diff()

    return data

def apply_strategy(data, return_series=False):
    bullish_conditions = (
        (data["EMA5"] > data["EMA13"])
        & (data["MACD"] < 0)
        & (data["Signal_Line"] < 0)
        & (data["MACD"] > data["Signal_Line"])
        & (data["EMA233_Slope"] > 0)
        & (data["Close"].shift(1) > data["LowLevel"].shift(1))
        & (data["RSI"].shift(1) > data["RSI"].shift(2))
    )

    bearish_conditions = (
        (data["EMA5"] < data["EMA13"])
        & (data["MACD"] > 0)
        & (data["Signal_Line"] > 0)
        & (data["MACD"] < data["Signal_Line"])
        & (data["EMA233_Slope"] < 0)
        & (data["Close"].shift(1) < data["HighLevel"].shift(1))
        & (data["RSI"].shift(1) < data["RSI"].shift(2))
    )

    if return_series:
        signals = pd.Series(0, index=data.index)
        signals[bullish_conditions] = 1
        signals[bearish_conditions] = -1
        return signals

    if bullish_conditions.iloc[-1]:
        return 1  # Buy
    elif bearish_conditions.iloc[-1]:
        return -1 # Sell
    else:
        return 0

def process_stock(symbol, end_date):
    """Fetch and calculate for a single symbol."""
    start_date = end_date - datetime.timedelta(days=365 * 3) # Discord bot requests 3 years
    try:
        # Robust fetch using fallback handling
        data = get_stock_data(symbol, start_date=start_date, end_date=end_date)
        
        if data is None or data.empty or len(data) < 233:
            return None

        current_price = data['Close'].iloc[-1]
        data = calculate_indicators(data)
        
        # Determine signal based on strategy
        signal = apply_strategy(data)
        
        if signal != 0:
            return {
                "Symbol": symbol, 
                "Signal": "Buy" if signal == 1 else "Sell", 
                "Current Price": round(current_price, 2)
            }
        return None
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        return None

def run_screener(stock_list, progress_callback=None):
    """
    Run strategy across a list of symbols multi-threaded.
    Yields progress dicts if a callback is passed to update Streamlit.
    """
    end_date = datetime.datetime.now()
    results = []
    total = len(stock_list)
    
    # We restrict max_workers to prevent instantly blowing past rate limits if on Finnhub
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_symbol = {executor.submit(process_stock, sym, end_date): sym for sym in stock_list}
        
        for i, future in enumerate(as_completed(future_to_symbol)):
            sym = future_to_symbol[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"{sym} generated an exception: {e}")
                
            # If using fallback APIs heavily, avoid API limit exhaustion
            time.sleep(0.05) 
                
            if progress_callback:
                progress_callback(i + 1, total, sym)

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values("Signal", ascending=False)
    else:
        df_results = pd.DataFrame(columns=["Symbol", "Signal", "Current Price"])
        
    return df_results

import os
import resend
import base64
from datetime import datetime
from fpdf import FPDF
from scrapers import get_crypto_fng, get_naaim, get_vix_data, get_td_sequential, scrape_with_playwright
from market_screener import run_screener, WATCH_LIST, SP500_LIST, NASDAQ100_LIST

class MarketPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, f"Daily Market Intelligence Report - {datetime.today().strftime('%Y-%m-%d')}", border=False, ln=True, align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, "Automated Quant Dashboard Analytics", border=False, ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(market_summary, td_data, screener_data):
    pdf = MarketPDF()
    pdf.add_page()
    
    # --- Part 1: Dashboard Summary ---
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, "1. Market Indicators Summary", ln=True)
    pdf.set_font('helvetica', '', 11)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 8, "Indicator", border=1, fill=True)
    pdf.cell(90, 8, "Value", border=1, fill=True, ln=True)
    
    for label, val in market_summary.items():
        pdf.cell(90, 8, str(label), border=1)
        pdf.cell(90, 8, str(val), border=1, ln=True)
    
    pdf.ln(10)
    
    # --- Part 2: Buy / Sell Screener Signals ---
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, "2. Market Screener Signals (Watchlist)", ln=True)
    pdf.set_font('helvetica', '', 10)
    
    if not screener_data.empty:
        # Table Header
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 8, "Symbol", border=1, fill=True)
        pdf.cell(30, 8, "Signal", border=1, fill=True)
        pdf.cell(40, 8, "Price", border=1, fill=True)
        pdf.cell(80, 8, "Sector / Info", border=1, fill=True, ln=True)
        
        for _, row in screener_data.iterrows():
            # Apply color to Signal
            original_draw = pdf.draw_color
            if row['Signal'] == 'Buy':
                pdf.set_text_color(0, 128, 0) # Green
            elif row['Signal'] == 'Sell':
                pdf.set_text_color(200, 0, 0) # Red
            
            pdf.cell(30, 8, str(row['Symbol']), border=1)
            pdf.cell(30, 8, str(row['Signal']), border=1)
            pdf.set_text_color(0, 0, 0) # Reset
            pdf.cell(40, 8, f"${row['Current Price']:.2f}", border=1)
            pdf.cell(80, 8, str(row.get('Sector', 'N/A')), border=1, ln=True)
    else:
        pdf.cell(0, 10, "No active buy/sell signals captured today.", ln=True)
    
    pdf.ln(10)

    # --- Part 3: TD Sequential ---
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, "3. TD Sequential Snapshot", ln=True)
    pdf.set_font('helvetica', '', 10)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 8, "Symbol", border=1, fill=True)
    pdf.cell(40, 8, "Price", border=1, fill=True)
    pdf.cell(100, 8, "Setup Status", border=1, fill=True, ln=True)
    
    for sym, data in td_data.items():
        pdf.cell(40, 8, str(sym), border=1)
        pdf.cell(40, 8, str(data.get("Current Price", "N/A")), border=1)
        pdf.cell(100, 8, str(data.get("TD", "N/A")), border=1, ln=True)

    file_path = f"market_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(file_path)
    return file_path

def collect_all_data():
    print("Collecting Dashboard Indicators...")
    naaim = get_naaim()
    crypto_fng = get_crypto_fng()
    vix_data = get_vix_data()
    td_data = get_td_sequential()
    pw = scrape_with_playwright()

    # Screener logic (running on all three lists: SP500, NASDAQ100, WATCH_LIST)
    print("Running Advanced Market Screener on all lists...")
    combined_list = list(set(SP500_LIST + NASDAQ100_LIST + WATCH_LIST))
    screener_results = run_screener(combined_list)
    
    # Calculate AAII Spread
    aaii_dict = pw.get("AAII", {})
    try:
        spread = f"{float(aaii_dict.get('Bullish', '0').replace('%','')) - float(aaii_dict.get('Bearish', '0').replace('%','')):+.2f}%"
    except:
        spread = "N/A"

    summary = {
        "CNN Fear & Greed": pw.get('CNNFearGreed', 'N/A'),
        "Crypto Fear & Greed": crypto_fng,
        "NAAIM Exposure": naaim.get('value', 'N/A') if isinstance(naaim, dict) else naaim,
        "AAII Bull-Bear Spread": spread,
        "VIX": vix_data.get('VIX', 'N/A')
    }
    
    return summary, td_data, screener_results

if __name__ == "__main__":
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    TO_EMAIL = os.environ.get("TO_EMAIL")

    if not RESEND_API_KEY or not TO_EMAIL:
        print("Missing RESEND_API_KEY or TO_EMAIL environment variables.")
        exit(1)

    resend.api_key = RESEND_API_KEY
    
    market_summary, td_data, screener_results = collect_all_data()
    
    # 1. Generate PDF
    print("Generating PDF Attachment...")
    pdf_path = generate_pdf_report(market_summary, td_data, screener_results)
    
    # 2. Binary content for Resend
    with open(pdf_path, "rb") as f:
        pdf_content = list(f.read()) # Resend expects a list of bytes if using legacy/certain methods, or just binary
    
    # 3. HTML Body for Email
    today_str = datetime.today().strftime('%Y-%m-%d')
    html_body = f"<h2>Market Insights for {today_str}</h2><p>Please find the attached PDF market intelligence report. It contains real-time indicators and buy/sell signals.</p>"

    # 4. Send with Attachment
    print(f"Sending report to {TO_EMAIL}...")
    try:
        # Using base64 encoding for attachment
        with open(pdf_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode()

        params = {
            "from": "Market Bot <onboarding@resend.dev>",
            "to": TO_EMAIL,
            "subject": f"🎯 [{today_str}] Market Intelligence Report",
            "html": html_body,
            "attachments": [
                {
                    "content": encoded_pdf,
                    "filename": f"Market_Report_{today_str}.pdf"
                }
            ]
        }
        
        r = resend.Emails.send(params)
        print(f"Success! ID: {r.get('id')}")
        
        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

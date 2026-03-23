import os
import resend
from datetime import datetime
from scrapers import get_crypto_fng, get_naaim, get_vix_data, get_td_sequential, scrape_with_playwright

def get_html_report():
    print("Collecting Market Data...")
    naaim = get_naaim()
    crypto_fng = get_crypto_fng()
    vix_data = get_vix_data()
    td_data = get_td_sequential()
    pw = scrape_with_playwright()

    # Determine AAII Spread
    aaii_dict = pw.get("AAII", {})
    bull = aaii_dict.get("Bullish", "0").replace('%', '')
    bear = aaii_dict.get("Bearish", "0").replace('%', '')
    try:
        aaii_spread = f"{float(bull) - float(bear):+.2f}%"
    except:
        aaii_spread = "N/A"

    today_str = datetime.today().strftime('%Y-%m-%d')
    
    html_content = f"""
    <h2>📈 Daily Market Intelligence Report - {today_str}</h2>
    
    <h3>🚦 Market Dashboard Summary</h3>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Indicator</th><th>Value</th>
        </tr>
        <tr><td>CNN Fear & Greed</td><td>{pw.get('CNNFearGreed', 'N/A')}</td></tr>
        <tr><td>Crypto Fear & Greed</td><td>{crypto_fng}</td></tr>
        <tr><td>NAAIM Exposure Index</td><td>{naaim.get('value', 'N/A') if isinstance(naaim, dict) else naaim}</td></tr>
        <tr><td>Trading Logic Breadth</td><td>{pw.get('TradingLogic', 'N/A')}</td></tr>
        <tr><td>AAII Bull-Bear Spread</td><td>{aaii_spread}</td></tr>
        <tr><td>VIX</td><td>{vix_data.get('VIX', 'N/A')}</td></tr>
    </table>

    <br>
    <h3>🔢 TD Sequential Snapshot</h3>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Symbol</th><th>Current Price</th><th>Last Close</th><th>TD Setup</th>
        </tr>
    """

    for sym, data in td_data.items():
        curr_price = data.get("Current Price", data.get("Price", "N/A"))
        last_close = data.get("Last Close", "N/A")
        td_status = data.get("TD", "N/A")
        html_content += f"<tr><td>{sym}</td><td>{curr_price}</td><td>{last_close}</td><td>{td_status}</td></tr>"

    html_content += """
    </table>
    <br><hr>
    <p><i>Automated report sent by GitHub Actions & Streamlit Dashboard Server.</i></p>
    """
    
    return html_content, today_str


if __name__ == "__main__":
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    TO_EMAIL = os.environ.get("TO_EMAIL")

    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY environment variable not found.")
        exit(1)
    if not TO_EMAIL:
        print("Error: TO_EMAIL environment variable not found. Please set it to the email address you want to receive reports.")
        exit(1)

    # Initialize Resend
    resend.api_key = RESEND_API_KEY

    # Generate HTML content
    html_body, today_date = get_html_report()

    # Send Email
    print(f"Sending email via Resend to {TO_EMAIL}...")
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": TO_EMAIL,
            "subject": f"[{today_date}] Daily Market Intelligence Report",
            "html": html_body
        })
        print("Success! Email sent. ID:", r.get('id'))
    except Exception as e:
        print("Failed to send email:")
        print(e)
        exit(1)

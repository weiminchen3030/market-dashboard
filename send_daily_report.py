"""
Daily Market Screener Report
────────────────────────────
Runs automatically via macOS launchd every weekday 30 min before US market close.
Scans S&P 500, NASDAQ 100, and Watchlist in parallel, generates a PDF, and emails it.

Setup:  copy .env.example → .env  and fill in your credentials.
"""

import os
import sys
import base64
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ── Load .env file (if python-dotenv is installed) ────────────────────────────
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # fall back to pre-set environment variables

import resend
from fpdf import FPDF
from market_screener import run_screener, SP500_LIST, NASDAQ100_LIST, WATCH_LIST

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Universe definitions ──────────────────────────────────────────────────────
UNIVERSES = {
    "S&P 500":    SP500_LIST,
    "NASDAQ 100": NASDAQ100_LIST,
    "Watchlist":  WATCH_LIST,
}


# ─────────────────────────────────────────────────────────────────────────────
# PDF Generation
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_doc_option("core_fonts_encoding", "utf-8")

    def header(self):
        self.set_font("helvetica", "B", 15)
        self.cell(
            0, 10,
            f"Advanced Market Screener - {datetime.today().strftime('%A, %B %d %Y')}",
            ln=True, align="C",
        )
        self.set_font("helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(
            0, 7,
            f"Generated {datetime.now().strftime('%H:%M')} local time  |  30 min before US market close",
            ln=True, align="C",
        )
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def footer(self):
        self.set_y(-13)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f"Page {self.page_no()}  ·  Antigravity Quant Dashboard", align="C")
        self.set_text_color(0, 0, 0)


def _section_header(pdf, text, r=30, g=30, b=50):
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 9, f"  {text}", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _signal_table(pdf, df, signal_type):
    """Render a Buy or Sell sub-table."""
    sub = df[df["Signal"] == signal_type]
    if sub.empty:
        return

    is_buy = signal_type == "Buy"
    color  = (0, 140, 0) if is_buy else (180, 0, 0)
    label  = "🟢 Buy Signals" if is_buy else "🔴 Sell Signals"

    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*color)
    pdf.cell(0, 8, label, ln=True)
    pdf.set_text_color(0, 0, 0)

    # Table header
    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for col, w in [("Symbol", 45), ("Signal", 35), ("Current Price", 50)]:
        pdf.cell(w, 8, col, border=1, fill=True)
    pdf.ln()

    # Rows
    pdf.set_font("helvetica", "", 9)
    for _, row in sub.iterrows():
        pdf.cell(45, 7, str(row["Symbol"]), border=1)
        pdf.set_text_color(*color)
        pdf.cell(35, 7, str(row["Signal"]), border=1)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 7, f"${row['Current Price']:.2f}", border=1)
        pdf.ln()

    pdf.ln(5)


def generate_pdf(all_results: dict) -> str:
    """Build the full multi-page PDF and return its file path."""
    pdf = ScreenerPDF()

    # ── Page 1: Summary ──────────────────────────────────────────────────────
    pdf.add_page()
    _section_header(pdf, "Summary — All Universes")

    # Summary table header
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(50, 50, 80)
    pdf.set_text_color(255, 255, 255)
    for col, w in [("Universe", 70), ("Total Signals", 40), ("🟢 Buy", 35), ("🔴 Sell", 35)]:
        pdf.cell(w, 9, col, border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    grand_buy = grand_sell = 0
    for name, df in all_results.items():
        buy_ct  = len(df[df["Signal"] == "Buy"])  if not df.empty else 0
        sell_ct = len(df[df["Signal"] == "Sell"]) if not df.empty else 0
        grand_buy  += buy_ct
        grand_sell += sell_ct

        pdf.set_font("helvetica", "", 10)
        pdf.cell(70, 8, name, border=1)
        pdf.cell(40, 8, str(buy_ct + sell_ct), border=1)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(35, 8, str(buy_ct), border=1)
        pdf.set_text_color(180, 0, 0)
        pdf.cell(35, 8, str(sell_ct), border=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    # Grand total row
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(70, 8, "TOTAL", border=1, fill=True)
    pdf.cell(40, 8, str(grand_buy + grand_sell), border=1, fill=True)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(35, 8, str(grand_buy), border=1, fill=True)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(35, 8, str(grand_sell), border=1, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()

    pdf.ln(8)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "Strategy: EMA 5/13 crossover · MACD baseline validation · RSI divergence · 233-day trend slope", ln=True)
    pdf.set_text_color(0, 0, 0)

    # ── Per-Universe Detail Pages ─────────────────────────────────────────────
    for name, df in all_results.items():
        pdf.add_page()
        _section_header(pdf, f"Universe: {name}", r=20, g=40, b=80)

        if df.empty:
            pdf.set_font("helvetica", "I", 10)
            pdf.cell(0, 10, "No Buy or Sell signals detected today.", ln=True)
            continue

        _signal_table(pdf, df, "Buy")
        _signal_table(pdf, df, "Sell")

    out = f"/tmp/screener_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf.output(out)
    log.info(f"PDF saved → {out}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Screener Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_screeners() -> dict:
    """Run S&P 500, NASDAQ 100, and Watchlist screeners in parallel."""
    results = {}

    def _scan(name, lst):
        log.info(f"  → Scanning {name} ({len(lst)} symbols)…")
        return name, run_screener(lst)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_scan, name, lst): name for name, lst in UNIVERSES.items()}
        for fut in futures:
            name, df = fut.result()
            results[name] = df
            buy_ct  = len(df[df["Signal"] == "Buy"])  if not df.empty else 0
            sell_ct = len(df[df["Signal"] == "Sell"]) if not df.empty else 0
            log.info(f"  ✓ {name}: {buy_ct} buy, {sell_ct} sell")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Email
# ─────────────────────────────────────────────────────────────────────────────

def send_report_email(pdf_path: str, all_results: dict):
    api_key    = os.environ.get("RESEND_API_KEY", "").strip()
    to_email   = os.environ.get("TO_EMAIL", "").strip()
    from_email = os.environ.get("FROM_EMAIL", "Market Bot <onboarding@resend.dev>").strip()

    if not api_key or not to_email:
        log.error("Missing RESEND_API_KEY or TO_EMAIL — check your .env file.")
        sys.exit(1)

    resend.api_key = api_key
    today_str = datetime.today().strftime("%Y-%m-%d")

    grand_buy = grand_sell = 0
    summary_rows_html = ""
    detail_sections_html = ""

    for name, df in all_results.items():
        buy_df  = df[df["Signal"] == "Buy"]  if not df.empty else df.__class__()
        sell_df = df[df["Signal"] == "Sell"] if not df.empty else df.__class__()
        b = len(buy_df)
        s = len(sell_df)
        grand_buy  += b
        grand_sell += s

        # Summary row
        summary_rows_html += (
            f"<tr>"
            f"<td style='padding:6px 12px'>{name}</td>"
            f"<td style='padding:6px 12px;color:#009900;font-weight:bold'>{b}</td>"
            f"<td style='padding:6px 12px;color:#cc0000;font-weight:bold'>{s}</td>"
            f"</tr>"
        )

        # Buy pills
        buy_pills = ""
        for _, row in buy_df.iterrows():
            buy_pills += (
                f"<span style='display:inline-block;background:#e6f9ee;color:#007700;"
                f"border:1px solid #99ddaa;border-radius:4px;padding:3px 8px;"
                f"margin:3px;font-size:13px;font-weight:bold'>"
                f"{row['Symbol']} <span style='font-weight:normal'>${row['Current Price']:.2f}</span>"
                f"</span>"
            )

        # Sell pills
        sell_pills = ""
        for _, row in sell_df.iterrows():
            sell_pills += (
                f"<span style='display:inline-block;background:#fff0f0;color:#cc0000;"
                f"border:1px solid #ffaaaa;border-radius:4px;padding:3px 8px;"
                f"margin:3px;font-size:13px;font-weight:bold'>"
                f"{row['Symbol']} <span style='font-weight:normal'>${row['Current Price']:.2f}</span>"
                f"</span>"
            )

        buy_block = (
            f"<div style='margin-bottom:8px'><b style='color:#007700'>Buy ({b})</b><br>{buy_pills}</div>"
            if b > 0 else
            "<div style='color:#aaa;font-size:12px;margin-bottom:8px'>No buy signals</div>"
        )
        sell_block = (
            f"<div><b style='color:#cc0000'>Sell ({s})</b><br>{sell_pills}</div>"
            if s > 0 else
            "<div style='color:#aaa;font-size:12px'>No sell signals</div>"
        )

        detail_sections_html += (
            f"<div style='margin-top:18px'>"
            f"<div style='background:#1a1a2e;color:#fff;padding:7px 12px;font-weight:bold;"
            f"border-radius:4px 4px 0 0;font-size:14px'>{name}</div>"
            f"<div style='border:1px solid #ddd;border-top:none;padding:10px 12px;"
            f"border-radius:0 0 4px 4px'>"
            f"{buy_block}"
            f"<hr style='border:none;border-top:1px solid #eee;margin:8px 0'>"
            f"{sell_block}"
            f"</div></div>"
        )

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:auto">
      <h2 style="color:#1a1a2e">Advanced Market Screener &mdash; {today_str}</h2>
      <p>Automated scan ran <b>30 minutes before US market close</b>.</p>

      <table border="1" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;width:100%;font-size:14px">
        <thead style="background:#1a1a2e;color:#fff">
          <tr>
            <th style="padding:8px 12px;text-align:left">Universe</th>
            <th style="padding:8px 12px">Buy</th>
            <th style="padding:8px 12px">Sell</th>
          </tr>
        </thead>
        <tbody>{summary_rows_html}</tbody>
        <tfoot style="background:#f0f0f0;font-weight:bold">
          <tr>
            <td style="padding:6px 12px">TOTAL</td>
            <td style="padding:6px 12px;color:#009900">{grand_buy}</td>
            <td style="padding:6px 12px;color:#cc0000">{grand_sell}</td>
          </tr>
        </tfoot>
      </table>

      <h3 style="margin-top:24px;color:#1a1a2e">Signal Details</h3>
      {detail_sections_html}

      <p style="color:#aaa;font-size:11px;margin-top:20px">
        Strategy: EMA 5/13 | MACD baseline | RSI divergence | 233-day trend slope<br>
        Full details also attached as PDF.
      </p>
    </div>
    """

    with open(pdf_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    params = {
        "from":    from_email,
        "to":      to_email,
        "subject": f"🎯 [{today_str}] Screener — {grand_buy}📈 Buy · {grand_sell}📉 Sell",
        "html":    html_body,
        "attachments": [
            {"content": encoded, "filename": f"Screener_{today_str}.pdf"}
        ],
    }

    r = resend.Emails.send(params)
    log.info(f"✅ Email sent — ID: {r.get('id')}  →  {to_email}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Skip weekends (launchd doesn't filter weekdays natively)
    if datetime.today().weekday() >= 5:
        log.info("Weekend — skipping screener run.")
        sys.exit(0)

    log.info(f"🚀 Daily screener starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    log.info("📡 Running screeners in parallel…")
    all_results = run_all_screeners()

    log.info("📄 Generating PDF report…")
    pdf_path = generate_pdf(all_results)

    log.info("📧 Sending email…")
    send_report_email(pdf_path, all_results)

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    log.info("✅ All done!")

"""
NIFTY Index Performance Dashboard — Weekly Refresh Script
----------------------------------------------------------
Run every Friday after 5:00 PM IST.
- Fetches weekly closes for all NIFTY indices + constituent stocks
- Reads stocks.txt (one ticker per line, e.g. HDFCBANK or HDFCBANK.NS)
  and shows a pinned "My Watchlist" row at the top of the dashboard
- Saves nifty_data.csv, nifty_stocks_data.csv, nifty_watchlist_data.csv
- Opens interactive dashboard — click any index / watchlist to drill into stocks

Requirements (install once):
    pip install yfinance pandas requests

Usage:
    python nifty_refresh.py

stocks.txt format (one ticker per line, # lines are comments):
    # My picks
    HDFCBANK
    RELIANCE
    INFY
    DIXON          <- .NS appended automatically if missing
"""

import yfinance as yf
import pandas as pd
import json, os, sys, webbrowser
from datetime import datetime

# ── Index definitions ─────────────────────────────────────────────────────────
INDICES = [
    ("Nifty 50",           "^NSEI"),
    ("Nifty Next 50",      "^NSMIDCP"),
    ("Nifty 100",          "^CNX100"),
    ("Nifty 200",          "^CNX200"),
    ("Nifty 500",          "^CRSLDX"),
    ("Nifty Midcap 50",    "^NSEMDCP50"),
    ("Nifty Midcap 100",   "NIFTY_MIDCAP_100.NS"),
    ("Nifty Smallcap 100", "^CNXSC"),
    ("Nifty Smallcap 250", "NIFTYSMLCAP250.NS"),
    ("Nifty Bank",         "^NSEBANK"),
    ("Nifty IT",           "^CNXIT"),
    ("Nifty Auto",         "^CNXAUTO"),
    ("Nifty FMCG",         "^CNXFMCG"),
    ("Nifty Pharma",       "^CNXPHARMA"),
    ("Nifty Fin Service",  "NIFTY_FIN_SERVICE.NS"),
    ("Nifty Metal",        "^CNXMETAL"),
    ("Nifty Realty",       "^CNXREALTY"),
    ("Nifty Energy",       "^CNXENERGY"),
    ("Nifty Media",        "^CNXMEDIA"),
    ("Nifty Infra",        "^CNXINFRA"),
    ("Nifty PSE",          "^CNXPSE"),
    ("Nifty PSU Bank",     "^CNXPSUBANK"),
    ("Nifty Consumption",  "^CNXCONSUM"),
    ("Nifty Commodities",  "^CNXCMDT"),
    ("Nifty Services",     "^CNXSERVICE"),
    ("Nifty MNC",          "^CNXMNC"),
    ("Nifty CPSE",         "NIFTY_CPSE.NS"),
    ("Nifty Healthcare",   "NIFTY_HEALTHCARE.NS"),
    ("Nifty India Mfg",    "NIFTY_INDIA_MFG.NS"),
]

# ── Constituent stocks per index (Yahoo Finance .NS tickers) ──────────────────
CONSTITUENTS = {
    "Nifty 50": [
        "ADANIENT.NS","ADANIPORTS.NS","APOLLOHOSP.NS","ASIANPAINT.NS","AXISBANK.NS",
        "BAJAJ-AUTO.NS","BAJFINANCE.NS","BAJAJFINSV.NS","BEL.NS","BPCL.NS",
        "BHARTIARTL.NS","BRITANNIA.NS","CIPLA.NS","COALINDIA.NS","DRREDDY.NS",
        "EICHERMOT.NS","GRASIM.NS","HCLTECH.NS","HDFCBANK.NS","HDFCLIFE.NS",
        "HEROMOTOCO.NS","HINDALCO.NS","HINDUNILVR.NS","ICICIBANK.NS","ITC.NS",
        "INDUSINDBK.NS","INFY.NS","JSWSTEEL.NS","KOTAKBANK.NS","LT.NS",
        "LTM.NS","M&M.NS","MARUTI.NS","NESTLEIND.NS","NTPC.NS",
        "ONGC.NS","POWERGRID.NS","RELIANCE.NS","SBILIFE.NS","SHRIRAMFIN.NS",
        "SBIN.NS","SUNPHARMA.NS","TCS.NS","TATACONSUM.NS","TMPV.NS",
        "TATASTEEL.NS","TECHM.NS","TITAN.NS","ULTRACEMCO.NS","WIPRO.NS",
    ],
    "Nifty Bank": [
        "AUBANK.NS","AXISBANK.NS","BANDHANBNK.NS","FEDERALBNK.NS","HDFCBANK.NS",
        "ICICIBANK.NS","IDFCFIRSTB.NS","INDUSINDBK.NS","KOTAKBANK.NS","PNB.NS",
        "SBIN.NS","BANKBARODA.NS",
    ],
    "Nifty IT": [
        "COFORGE.NS","HCLTECH.NS","INFY.NS","LTM.NS","MPHASIS.NS",
        "PERSISTENT.NS","TCS.NS","TECHM.NS","WIPRO.NS","OFSS.NS",
    ],
    "Nifty Auto": [
        "APOLLOTYRE.NS","ASHOKLEY.NS","BAJAJ-AUTO.NS","BALKRISIND.NS","BHARATFORG.NS",
        "BOSCHLTD.NS","EICHERMOT.NS","HEROMOTOCO.NS","M&M.NS","MARUTI.NS",
        "MOTHERSON.NS","MRF.NS","TMPV.NS","TVSMOTOR.NS","TIINDIA.NS",
    ],
    "Nifty FMCG": [
        "BRITANNIA.NS","COLPAL.NS","DABUR.NS","GODREJCP.NS","HINDUNILVR.NS",
        "ITC.NS","MARICO.NS","NESTLEIND.NS","TATACONSUM.NS","UBL.NS",
        "UNITDSPR.NS","RADICO.NS","EMAMILTD.NS","PGHH.NS","VBL.NS",
    ],
    "Nifty Pharma": [
        "AUROPHARMA.NS","CIPLA.NS","DIVISLAB.NS","DRREDDY.NS","GLENMARK.NS",
        "GRANULES.NS","IPCALAB.NS","LAURUSLABS.NS","LUPIN.NS","SUNPHARMA.NS",
        "TORNTPHARM.NS","ALKEM.NS","BIOCON.NS","ABBOTINDIA.NS","MANKIND.NS",
    ],
    "Nifty Metal": [
        "ADANIENT.NS","APLAPOLLO.NS","COALINDIA.NS","HINDALCO.NS","HINDCOPPER.NS",
        "JSWSTEEL.NS","NATIONALUM.NS","NMDC.NS","SAIL.NS","TATASTEEL.NS",
        "VEDL.NS","WELCORP.NS","MOIL.NS","APLAPOLLO.NS","RATNAMANI.NS",
    ],
    "Nifty Realty": [
        "BRIGADE.NS","DLF.NS","GODREJPROP.NS","LODHA.NS","MAHLIFE.NS",
        "OBEROIRLTY.NS","PHOENIXLTD.NS","PRESTIGE.NS","SOBHA.NS","SUNTECK.NS",
    ],
    "Nifty Energy": [
        "ADANIGREEN.NS","ADANIPOWER.NS","BPCL.NS","GAIL.NS","IOC.NS",
        "NTPC.NS","ONGC.NS","POWERGRID.NS","RELIANCE.NS","TATAPOWER.NS",
    ],
    "Nifty PSU Bank": [
        "BANKBARODA.NS","CANBK.NS","INDIANB.NS","IOB.NS","PNB.NS",
        "SBIN.NS","UCOBANK.NS","UNIONBANK.NS","MAHABANK.NS","BANKINDIA.NS",
    ],
    "Nifty Fin Service": [
        "AXISBANK.NS","BAJFINANCE.NS","BAJAJFINSV.NS","CHOLAFIN.NS","HDFCBANK.NS",
        "HDFCLIFE.NS","ICICIBANK.NS","ICICIGI.NS","KOTAKBANK.NS","LICHSGFIN.NS",
        "M&MFIN.NS","MUTHOOTFIN.NS","PFC.NS","RECLTD.NS","SBICARD.NS",
        "SBILIFE.NS","SHRIRAMFIN.NS",
    ],
    "Nifty Infra": [
        "ADANIPORTS.NS","ADANIGREEN.NS","BHARTIARTL.NS","BPCL.NS","GAIL.NS",
        "GMRAIRPORT.NS","IOC.NS","IRB.NS","LT.NS","NTPC.NS",
        "ONGC.NS","POWERGRID.NS","RELIANCE.NS","TATAPOWER.NS","NBCC.NS",
    ],
    "Nifty Healthcare": [
        "APOLLOHOSP.NS","CIPLA.NS","DIVISLAB.NS","DRREDDY.NS","FORTIS.NS",
        "LALPATHLAB.NS","LUPIN.NS","MAXHEALTH.NS","METROPOLIS.NS","SUNPHARMA.NS",
        "TORNTPHARM.NS","AUROPHARMA.NS","MANKIND.NS",
    ],
    "Nifty PSE": [
        "BPCL.NS","COALINDIA.NS","GAIL.NS","HINDPETRO.NS","IOC.NS",
        "NTPC.NS","ONGC.NS","POWERGRID.NS","SAIL.NS","SBIN.NS",
        "BEL.NS","BHEL.NS","HAL.NS","NMDC.NS","RECLTD.NS",
    ],
    "Nifty Media": [
        "PVRINOX.NS","SUNTV.NS","ZEEL.NS","NAZARA.NS","TVTODAY.NS",
        "NETWORK18.NS","JAGRAN.NS","SAREGAMA.NS","TIPSMUSIC.NS","DISHTV.NS",
    ],
}

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR         = os.path.dirname(os.path.abspath(__file__))
CSV_INDEX_PATH     = os.path.join(SCRIPT_DIR, "nifty_data.csv")
CSV_STOCKS_PATH    = os.path.join(SCRIPT_DIR, "nifty_stocks_data.csv")
CSV_WATCHLIST_PATH = os.path.join(SCRIPT_DIR, "nifty_watchlist_data.csv")
HTML_PATH              = os.path.join(SCRIPT_DIR, "index.html")
LOOKUP_SERVER_PATH     = os.path.join(SCRIPT_DIR, "lookup_server.py")
NETLIFY_FUNC_DIR       = os.path.join(SCRIPT_DIR, "netlify", "functions")
NETLIFY_FUNC_PATH      = os.path.join(NETLIFY_FUNC_DIR, "lookup.js")
NETLIFY_TOML_PATH      = os.path.join(SCRIPT_DIR, "netlify.toml")
PACKAGE_JSON_PATH      = os.path.join(SCRIPT_DIR, "package.json")
WATCHLIST_FILE         = os.path.join(SCRIPT_DIR, "stocks.txt")
WATCHLIST_KEY          = "\u2605 My Watchlist"   # ★ My Watchlist

# ── Core fetch ────────────────────────────────────────────────────────────────
def fetch_weekly(ticker):
    raw = yf.download(ticker, period="1y", interval="1wk",
                      progress=False, auto_adjust=True)
    if raw.empty or len(raw) < 3:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        col = raw["Close"]
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
    else:
        col = raw["Close"]
    closes = col.dropna()
    rows = []
    for dt, close in closes.items():
        val = float(close)
        if val <= 0:          # skip zero / bad candles
            continue
        date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        rows.append({"date": date_str, "close": round(val, 2)})
    return rows

# ── Fetch all indices ─────────────────────────────────────────────────────────
def fetch_indices():
    all_rows, total = [], len(INDICES)
    for i, (name, ticker) in enumerate(INDICES, 1):
        print(f"  [{i:2d}/{total}] {name} ({ticker}) ... ", end="", flush=True)
        try:
            rows = fetch_weekly(ticker)
            if not rows:
                print("no data"); continue
            for r in rows:
                all_rows.append({"index_name": name, "ticker": ticker, **r})
            print(f"OK  ({len(rows)} weeks)")
        except Exception as e:
            print(f"ERROR: {e}")
    return pd.DataFrame(all_rows)

# ── Fetch constituent stocks ──────────────────────────────────────────────────
def fetch_stocks():
    all_rows = []
    items = list(CONSTITUENTS.items())
    for idx_i, (index_name, stocks) in enumerate(items, 1):
        print(f"\n  [{idx_i}/{len(items)}] {index_name} — {len(stocks)} stocks")
        for j, ticker in enumerate(stocks, 1):
            short = ticker.replace(".NS", "")
            print(f"      [{j:2d}/{len(stocks)}] {short} ... ", end="", flush=True)
            try:
                rows = fetch_weekly(ticker)
                if not rows:
                    print("no data"); continue
                for r in rows:
                    all_rows.append({
                        "index_name": index_name,
                        "stock_ticker": ticker,
                        "stock_name": short,
                        **r
                    })
                print(f"OK ({len(rows)} wks)")
            except Exception as e:
                print(f"ERROR: {e}")
    return pd.DataFrame(all_rows)

# ── Load & fetch watchlist ────────────────────────────────────────────────────
def load_watchlist():
    """Read stocks.txt; return list of .NS tickers. Returns [] if file missing."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    tickers = []
    with open(WATCHLIST_FILE, encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            t = raw.upper()
            if not t.endswith(".NS") and not t.startswith("^"):
                t += ".NS"
            tickers.append(t)
    return tickers

def fetch_watchlist(tickers):
    """Fetch weekly data for watchlist tickers. Returns DataFrame same shape as stk_df."""
    all_rows = []
    total = len(tickers)
    for j, ticker in enumerate(tickers, 1):
        short = ticker.replace(".NS", "")
        print(f"      [{j:2d}/{total}] {short} ... ", end="", flush=True)
        try:
            rows = fetch_weekly(ticker)
            if not rows:
                print("no data"); continue
            for r in rows:
                all_rows.append({
                    "index_name": WATCHLIST_KEY,
                    "stock_ticker": ticker,
                    "stock_name": short,
                    **r
                })
            print(f"OK ({len(rows)} wks)")
        except Exception as e:
            print(f"ERROR: {e}")
    return pd.DataFrame(all_rows)
def compute_stats(df, name_col="index_name"):
    results = []
    for name, group in df.groupby(name_col, sort=False):
        g = group.sort_values("date").reset_index(drop=True)
        # Drop any rows where close is 0 or NaN (incomplete candles)
        g = g[g["close"].notna() & (g["close"] > 0)].reset_index(drop=True)
        closes = g["close"].tolist()
        dts    = g["date"].tolist()
        n = len(closes)
        if n < 3:
            continue

        cur    = closes[-1]
        cur_dt = dts[-1]

        def w(k):
            idx = n - 1 - k
            return closes[idx] if idx >= 0 else None

        def wd(k):
            idx = n - 1 - k
            return dts[idx] if idx >= 0 else None

        def pct(a, b):
            if a is None or b is None or b == 0:
                return None
            return round(((a - b) / b) * 100, 2)

        # Period returns: 1W 2W 3W 4W 5W 6W 6M 1Y
        r1w = pct(cur, w(1));  r2w = pct(cur, w(2))
        r3w = pct(cur, w(3));  r4w = pct(cur, w(4))
        r5w = pct(cur, w(5));  r6w = pct(cur, w(6))
        r6m = pct(cur, w(26)); r1y = pct(cur, closes[0])

        # Closing values at each period baseline
        c1w = w(1);  c2w = w(2);  c3w = w(3);  c4w = w(4)
        c5w = w(5);  c6w = w(6);  c6m = w(26); c1y = closes[0]

        # Dates of each period baseline
        d1w = wd(1);  d2w = wd(2);  d3w = wd(3);  d4w = wd(4)
        d5w = wd(5);  d6w = wd(6);  d6m = wd(26); d1y = dts[0]

        mom = []
        for k in range(10, 0, -1):
            a, b = w(k-1), w(k)
            if a is None or b is None:
                mom.append(0)
            else:
                mom.append(1 if a > b else (-1 if a < b else 0))
        score = sum(mom)

        results.append({
            "name": name, "cur": cur, "cur_dt": cur_dt,
            "r1w": r1w,  "r2w": r2w,  "r3w": r3w,  "r4w": r4w,
            "r5w": r5w,  "r6w": r6w,  "r6m": r6m,  "r1y": r1y,
            "c1w": c1w,  "c2w": c2w,  "c3w": c3w,  "c4w": c4w,
            "c5w": c5w,  "c6w": c6w,  "c6m": c6m,  "c1y": c1y,
            "d1w": d1w,  "d2w": d2w,  "d3w": d3w,  "d4w": d4w,
            "d5w": d5w,  "d6w": d6w,  "d6m": d6m,  "d1y": d1y,
            "mom": mom, "score": score,
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)

def compute_stock_stats(df):
    result = {}
    for index_name in df["index_name"].unique():
        sub = df[df["index_name"] == index_name].copy()
        result[index_name] = compute_stats(sub, name_col="stock_name")
    return result

# ── Lookup infrastructure writers ────────────────────────────────────────────
def write_netlify_function():
    """Write netlify/functions/lookup.js — the serverless lookup endpoint."""
    os.makedirs(NETLIFY_FUNC_DIR, exist_ok=True)
    code = r"""// netlify/functions/lookup.js
// Netlify serverless function — called by the dashboard when hosted on Netlify.
// Fetches 1-year weekly closes from Yahoo Finance and computes the same stats
// as the Python nifty_refresh.py script.
//
// Deploy: just push to your Netlify-linked repo. No config needed.
// Dependency: yahoo-finance2  (listed in package.json at repo root)

const yahooFinance = require("yahoo-finance2").default;

exports.handler = async (event) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Content-Type": "application/json",
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers, body: "" };
  }

  const raw = (event.queryStringParameters || {}).tickers || "";
  if (!raw.trim()) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: "No tickers" }) };
  }

  const tickers = raw.split(",").map(t => {
    t = t.trim().toUpperCase();
    if (!t) return null;
    if (t.startsWith("^") || t.includes(".")) return t;
    return t + ".NS";
  }).filter(Boolean);

  const results = [];
  const errors  = [];

  for (const ticker of tickers) {
    try {
      const rows = await fetchWeekly(ticker);
      if (!rows || rows.length < 3) { errors.push(ticker + " (no data)"); continue; }
      const stat = computeOne(rows, ticker.replace(".NS", "").replace("^", ""));
      if (stat) results.push(stat);
      else errors.push(ticker + " (compute failed)");
    } catch (e) {
      errors.push(ticker + " (" + e.message + ")");
    }
  }

  return { statusCode: 200, headers, body: JSON.stringify({ results, errors }) };
};

async function fetchWeekly(ticker) {
  const result = await yahooFinance.historical(ticker, {
    period1: (() => { const d = new Date(); d.setFullYear(d.getFullYear() - 1); return d; })(),
    period2: new Date(),
    interval: "1wk",
  });
  if (!result || result.length < 3) return null;
  return result
    .filter(r => r.close && r.close > 0)
    .map(r => ({
      date: r.date.toISOString().slice(0, 10),
      close: Math.round(r.close * 100) / 100,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function computeOne(rows, displayName) {
  const closes = rows.map(r => r.close);
  const dts    = rows.map(r => r.date);
  const n      = closes.length;
  const cur    = closes[n - 1];
  const curDt  = dts[n - 1];

  const w  = k => { const i = n - 1 - k; return i >= 0 ? closes[i] : null; };
  const wd = k => { const i = n - 1 - k; return i >= 0 ? dts[i]   : null; };
  const pct = (a, b) => (a == null || b == null || b === 0) ? null : Math.round(((a - b) / b) * 10000) / 100;

  const mom = [];
  for (let k = 10; k >= 1; k--) {
    const a = w(k - 1), b = w(k);
    if (a == null || b == null) mom.push(0);
    else mom.push(a > b ? 1 : a < b ? -1 : 0);
  }
  const score = mom.reduce((s, v) => s + v, 0);

  return {
    name: displayName, cur, cur_dt: curDt,
    r1w: pct(cur, w(1)),  r2w: pct(cur, w(2)),
    r3w: pct(cur, w(3)),  r4w: pct(cur, w(4)),
    r5w: pct(cur, w(5)),  r6w: pct(cur, w(6)),
    r6m: pct(cur, w(26)), r1y: pct(cur, closes[0]),
    c1w: w(1),  c2w: w(2),  c3w: w(3),  c4w: w(4),
    c5w: w(5),  c6w: w(6),  c6m: w(26), c1y: closes[0],
    d1w: wd(1), d2w: wd(2), d3w: wd(3), d4w: wd(4),
    d5w: wd(5), d6w: wd(6), d6m: wd(26),d1y: dts[0],
    mom, score, momRank: 0,
  };
}
"""
    with open(NETLIFY_FUNC_PATH, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"  Saved \u2192 {NETLIFY_FUNC_PATH}")


def write_netlify_toml():
    """Write netlify.toml — tells Netlify where functions live and sets publish dir."""
    # Only write if it doesn't already exist (don't clobber user edits)
    if os.path.exists(NETLIFY_TOML_PATH):
        print(f"  Skipped {NETLIFY_TOML_PATH} (already exists)")
        return
    toml = """\
[build]
  publish = "."
  functions = "netlify/functions"

[functions]
  node_bundler = "esbuild"
"""
    with open(NETLIFY_TOML_PATH, "w", encoding="utf-8") as f:
        f.write(toml)
    print(f"  Saved \u2192 {NETLIFY_TOML_PATH}")


def write_package_json():
    """Write package.json with yahoo-finance2 dependency for the Netlify function."""
    if os.path.exists(PACKAGE_JSON_PATH):
        print(f"  Skipped {PACKAGE_JSON_PATH} (already exists)")
        return
    pkg = """\
{
  "name": "equipulse",
  "version": "1.0.0",
  "description": "NIFTY Index Dashboard",
  "dependencies": {
    "yahoo-finance2": "^2.11.3"
  }
}
"""
    with open(PACKAGE_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(pkg)
    print(f"  Saved \u2192 {PACKAGE_JSON_PATH}")


def write_lookup_server():
    """Write lookup_server.py next to index.html. Run it with: python lookup_server.py"""
    code = '''"""
EquiPulse — Runtime Stock Lookup Server
----------------------------------------
Run this alongside index.html to enable the live stock lookup feature.

    python lookup_server.py

Listens on http://localhost:7777
Endpoint: GET /lookup?tickers=HDFCBANK,RELIANCE,INFY

The dashboard calls this automatically when you type a ticker and press Lookup.
"""

import json, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import yfinance as yf
import pandas as pd


PORT = 7777


def fetch_weekly(ticker):
    raw = yf.download(ticker, period="1y", interval="1wk",
                      progress=False, auto_adjust=True)
    if raw.empty or len(raw) < 3:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        col = raw["Close"]
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
    else:
        col = raw["Close"]
    closes = col.dropna()
    rows = []
    for dt, close in closes.items():
        val = float(close)
        if val <= 0:
            continue
        date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        rows.append({"date": date_str, "close": round(val, 2)})
    return rows


def compute_one(ticker, display_name):
    rows = fetch_weekly(ticker)
    if not rows or len(rows) < 3:
        return None
    closes = [r["close"] for r in rows]
    dts    = [r["date"]  for r in rows]
    n = len(closes)
    cur    = closes[-1]
    cur_dt = dts[-1]

    def w(k):
        idx = n - 1 - k
        return closes[idx] if idx >= 0 else None

    def wd(k):
        idx = n - 1 - k
        return dts[idx] if idx >= 0 else None

    def pct(a, b):
        if a is None or b is None or b == 0:
            return None
        return round(((a - b) / b) * 100, 2)

    mom = []
    for k in range(10, 0, -1):
        a, b = w(k-1), w(k)
        if a is None or b is None:
            mom.append(0)
        else:
            mom.append(1 if a > b else (-1 if a < b else 0))
    score = sum(mom)

    return {
        "name": display_name, "cur": cur, "cur_dt": cur_dt,
        "r1w": pct(cur, w(1)),  "r2w": pct(cur, w(2)),
        "r3w": pct(cur, w(3)),  "r4w": pct(cur, w(4)),
        "r5w": pct(cur, w(5)),  "r6w": pct(cur, w(6)),
        "r6m": pct(cur, w(26)), "r1y": pct(cur, closes[0]),
        "c1w": w(1),  "c2w": w(2),  "c3w": w(3),  "c4w": w(4),
        "c5w": w(5),  "c6w": w(6),  "c6m": w(26), "c1y": closes[0],
        "d1w": wd(1), "d2w": wd(2), "d3w": wd(3), "d4w": wd(4),
        "d5w": wd(5), "d6w": wd(6), "d6m": wd(26),"d1y": dts[0],
        "mom": mom, "score": score, "momRank": 0,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("  [lookup]", fmt % args)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/lookup":
            self.send_response(404)
            self.end_headers()
            return

        qs = parse_qs(parsed.query)
        raw_tickers = qs.get("tickers", [""])[0]
        if not raw_tickers.strip():
            self._json({"error": "No tickers supplied"}, 400)
            return

        results = []
        errors  = []
        for t in [x.strip() for x in raw_tickers.split(",") if x.strip()]:
            display = t.upper()
            ticker  = display if display.endswith(".NS") or display.startswith("^") else display + ".NS"
            print(f"  Fetching {ticker} ...", end=" ", flush=True)
            try:
                stat = compute_one(ticker, display.replace(".NS", ""))
                if stat:
                    results.append(stat)
                    print("OK")
                else:
                    errors.append(t + " (no data)")
                    print("no data")
            except Exception as e:
                errors.append(t + " (" + str(e) + ")")
                print("ERROR:", e)

        self._json({"results": results, "errors": errors})

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"EquiPulse Lookup Server — listening on http://localhost:{PORT}")
    print("Open index.html in your browser, then use the Lookup bar to query any stock.")
    print("Press Ctrl+C to stop.\\n")
    try:
        HTTPServer(("localhost", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\\nStopped.")
        sys.exit(0)
'''
    with open(LOOKUP_SERVER_PATH, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"  Saved \u2192 {LOOKUP_SERVER_PATH}")


# ── HTML generation ───────────────────────────────────────────────────────────
# We build the HTML as a regular string (not f-string) to avoid
# conflicts between Python's {} and JavaScript's {} and ${}.
def generate_html(index_stats, stock_stats, watchlist_stats, as_of):
    index_json     = json.dumps(index_stats)
    stock_json     = json.dumps(stock_stats)
    watchlist_json = json.dumps(watchlist_stats)
    watchlist_key  = json.dumps(WATCHLIST_KEY)

    css = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
:root {
  --bg:#0d0f14; --surface:#13161d; --surface2:#1a1e28;
  --border:rgba(255,255,255,0.07); --border2:rgba(255,255,255,0.13);
  --text:#e8eaf0; --muted:#6b7280; --muted2:#9ca3af;
  --green:#10b981; --red:#ef4444; --accent:#6366f1;
  --mono:'IBM Plex Mono',monospace; --sans:'DM Sans',sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--sans);background:var(--bg);color:var(--text);font-size:13px}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;
  border-bottom:1px solid var(--border);background:var(--surface);flex-wrap:wrap;gap:10px}
.brand{font-family:var(--mono);font-size:14px;font-weight:500;letter-spacing:0.03em}
.asof{font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:2px}
.summary{display:flex;background:var(--surface);border-bottom:1px solid var(--border)}
.sc{flex:1;padding:10px 16px;border-right:1px solid var(--border)}
.sc:last-child{border-right:none}
.sl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.07em;font-family:var(--mono);margin-bottom:3px}
.sv{font-size:16px;font-weight:500;font-family:var(--mono)}
.pos{color:var(--green)} .neg{color:var(--red)} .neu{color:var(--muted2)}
.filters{display:flex;gap:10px;padding:8px 24px;border-bottom:1px solid var(--border);
  background:var(--surface);align-items:center;flex-wrap:wrap}
.filters label{font-size:11px;color:var(--muted);font-family:var(--mono)}
select{background:var(--surface2);color:var(--text);border:1px solid var(--border2);
  border-radius:6px;padding:4px 8px;font-size:12px;font-family:var(--mono);cursor:pointer}
input[type=text]{background:var(--surface2);color:var(--text);border:1px solid var(--border2);
  border-radius:6px;padding:4px 10px;font-size:12px;font-family:var(--mono);width:160px;outline:none}
input[type=text]:focus{border-color:var(--accent)}
.notebar{padding:6px 24px;font-size:11px;color:var(--muted);background:var(--surface2);
  border-bottom:1px solid var(--border);font-family:var(--mono)}
.tbl-wrap{overflow-x:auto;overflow-y:auto;height:calc(100vh - 185px)}
table{width:100%;border-collapse:collapse;min-width:960px;font-size:11.5px}
thead{position:sticky;top:0;z-index:5}
th{padding:8px 8px;text-align:right;font-family:var(--mono);font-size:10px;font-weight:500;
  color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;
  border-bottom:1px solid var(--border2);background:var(--surface2);
  white-space:nowrap;cursor:pointer;user-select:none}
th:hover{color:var(--text)}
th:first-child{text-align:left;position:sticky;left:0;z-index:6;background:var(--surface2);
  min-width:160px;padding-left:20px}
td{padding:6px 8px;text-align:right;border-bottom:1px solid var(--border);
  white-space:nowrap;font-family:var(--mono)}
td:first-child{text-align:left;position:sticky;left:0;background:var(--bg);z-index:2;
  font-family:var(--sans);font-weight:500;padding-left:20px;font-size:12px}
tr:hover td{background:var(--surface2)}
tr:hover td:first-child{background:var(--surface2)}
.mom{text-align:center;font-weight:500}
.mp{color:var(--green)} .mn{color:var(--red)} .mz{color:#374151}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:500;font-family:var(--mono)}
.bull{background:rgba(16,185,129,0.15);color:var(--green);border:1px solid rgba(16,185,129,0.25)}
.bear{background:rgba(239,68,68,0.15);color:var(--red);border:1px solid rgba(239,68,68,0.25)}
.ntrl{background:rgba(107,114,128,0.15);color:var(--muted2);border:1px solid rgba(107,114,128,0.2)}
.cur{color:#c7d2fe;font-weight:500}
.sa{color:var(--green);font-weight:600} .sn{color:var(--red);font-weight:600} .s0{color:var(--muted2)}
.drill-panel{display:none;position:fixed;top:0;right:0;width:78vw;height:100vh;
  background:var(--bg);border-left:1px solid var(--border2);z-index:1000;
  flex-direction:column;box-shadow:-8px 0 40px rgba(0,0,0,0.6)}
.drill-panel.open{display:flex}
.drill-header{display:flex;align-items:center;justify-content:space-between;
  padding:14px 20px;border-bottom:1px solid var(--border);background:var(--surface);flex-shrink:0}
.drill-title{font-family:var(--mono);font-size:13px;font-weight:500}
.drill-sub{font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:2px}
.drill-summary{display:flex;background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
.close-btn{background:var(--surface2);border:1px solid var(--border2);color:var(--text);
  border-radius:6px;padding:5px 14px;cursor:pointer;font-size:12px;font-family:var(--mono)}
.close-btn:hover{background:var(--surface)}
.drill-notebar{padding:5px 20px;font-size:11px;color:var(--muted);background:var(--surface2);
  border-bottom:1px solid var(--border);font-family:var(--mono);flex-shrink:0}
.drill-body{flex:1;overflow:auto}
.no-data-msg{padding:40px;text-align:center;color:var(--muted);font-family:var(--mono);font-size:12px}
.legend{display:flex;gap:16px;padding:10px 24px;border-top:1px solid var(--border);
  background:var(--surface);font-size:11px;color:var(--muted);flex-wrap:wrap;align-items:center}
.sticky-top{position:relative;z-index:50;background:var(--bg)}
.sort-asc::after{content:" ↑";color:var(--accent)}
.sort-desc::after{content:" ↓";color:var(--accent)}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:#2d3748;border-radius:3px}
.hdr-date{font-size:9px;color:var(--muted);font-weight:400;letter-spacing:0;text-transform:none;display:block;margin-top:1px}
th{line-height:1.25}
td{padding:5px 8px;vertical-align:top}
.watchlist-row td{background:rgba(99,102,241,0.07);border-bottom:1px solid rgba(99,102,241,0.2)}
.watchlist-row:hover td{background:rgba(99,102,241,0.14)}
.watchlist-row td:first-child{background:rgba(99,102,241,0.07)}
.watchlist-row:hover td:first-child{background:rgba(99,102,241,0.14)}
.watchlist-sep td{padding:0;height:3px;background:rgba(99,102,241,0.25);border:none}
/* ── Lookup bar ── */
.lookup-bar{display:flex;gap:8px;padding:7px 24px;border-bottom:1px solid var(--border);
  background:var(--surface);align-items:center;flex-wrap:wrap}
.lookup-bar label{font-size:11px;color:var(--muted);font-family:var(--mono)}
#lookupInput{width:340px;background:var(--surface2);color:var(--text);
  border:1px solid rgba(251,191,36,0.35);border-radius:6px;padding:4px 10px;
  font-size:12px;font-family:var(--mono);outline:none}
#lookupInput:focus{border-color:rgba(251,191,36,0.8);box-shadow:0 0 0 2px rgba(251,191,36,0.1)}
#lookupInput::placeholder{color:var(--muted)}
.lookup-btn{background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.35);
  border-radius:6px;padding:4px 14px;cursor:pointer;font-size:12px;font-family:var(--mono);
  font-weight:500;transition:background 0.15s}
.lookup-btn:hover{background:rgba(251,191,36,0.28)}
.lookup-btn:disabled{opacity:0.4;cursor:not-allowed}
.lookup-clear-btn{background:transparent;color:var(--muted);border:1px solid var(--border2);
  border-radius:6px;padding:4px 10px;cursor:pointer;font-size:11px;font-family:var(--mono)}
.lookup-clear-btn:hover{color:var(--text);border-color:var(--muted)}
#lookupStatus{font-size:11px;font-family:var(--mono);color:var(--muted)}
#lookupStatus.err{color:var(--red)}
/* Lookup result rows — amber highlight */
.lookup-row td{background:rgba(251,191,36,0.06);border-bottom:1px solid rgba(251,191,36,0.18)}
.lookup-row:hover td{background:rgba(251,191,36,0.12)}
.lookup-row td:first-child{background:rgba(251,191,36,0.06)}
.lookup-row:hover td:first-child{background:rgba(251,191,36,0.12)}
.lookup-sep td{padding:0;height:3px;background:rgba(251,191,36,0.3);border:none}
.lookup-remove{cursor:pointer;color:var(--muted);font-size:10px;margin-left:6px;
  opacity:0.6;font-family:var(--mono)}
.lookup-remove:hover{color:var(--red);opacity:1}
"""

    js = """
const INDEX_DATA    = """ + index_json + """;
const STOCK_DATA    = """ + stock_json + """;
const WATCHLIST     = """ + watchlist_json + """;
const WATCHLIST_KEY = """ + watchlist_key + """;

// Pre-assign momentum ranks (by score, descending)
const ranked = [...INDEX_DATA].sort((a,b) => b.score - a.score);
ranked.forEach((r,i) => { r.momRank = i+1; });
for (const idxName in STOCK_DATA) {
  const sr = [...STOCK_DATA[idxName]].sort((a,b) => b.score - a.score);
  sr.forEach((r,i) => { r.momRank = i+1; });
}
if (WATCHLIST.length > 0) {
  const wr = [...WATCHLIST].sort((a,b) => b.score - a.score);
  wr.forEach((r,i) => { r.momRank = i+1; });
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function fp(v)  { if(v==null||isNaN(v)) return '—'; return (v>=0?'+':'')+v.toFixed(2)+'%'; }
function fpr(v) { if(v==null||v===undefined) return '—'; return v.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function cc(v)  { if(v==null) return 'neu'; return v>0?'pos':v<0?'neg':'neu'; }
function fmtDate(d) {
  if(!d) return '';
  const dt = new Date(d);
  const day = dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short'});
  const yr  = String(dt.getFullYear()).slice(-2);
  return day + ' ' + yr;
}
function getMom(s) {
  if(s>=7)  return {l:'↑↑ Strong Bull', c:'bull'};
  if(s>=4)  return {l:'↑ Bull',         c:'bull'};
  if(s<=-7) return {l:'↓↓ Strong Bear', c:'bear'};
  if(s<=-4) return {l:'↓ Bear',         c:'bear'};
  return {l:'→ Neutral', c:'ntrl'};
}

function momCell(v) {
  const mc  = v===1?'mp':v===-1?'mn':'mz';
  const lbl = v===1?'+1':v===-1?'−1':'0';
  return '<td class="mom '+mc+'">'+lbl+'</td>';
}

// Period cell: shows % on top, closing value below
function pCell(pct, close, cls) {
  const pStr = fp(pct);
  const cStr = fpr(close);
  return '<td class="'+cls+'" style="line-height:1.3">'
    + '<div>'+pStr+'</div>'
    + '<div style="font-size:10px;color:var(--muted2);font-weight:400">'+cStr+'</div>'
    + '</td>';
}

function buildRows(data) {
  let h = '';
  data.forEach(r => {
    const m  = getMom(r.score);
    const sc = r.score>0?'sa':r.score<0?'sn':'s0';
    h += '<tr>';
    h += '<td>'+r.name+'</td>';
    h += '<td class="cur">'+fpr(r.cur)+'</td>';
    h += pCell(r.r1w, r.c1w, cc(r.r1w));
    h += pCell(r.r2w, r.c2w, cc(r.r2w));
    h += pCell(r.r3w, r.c3w, cc(r.r3w));
    h += pCell(r.r4w, r.c4w, cc(r.r4w));
    h += pCell(r.r5w, r.c5w, cc(r.r5w));
    h += pCell(r.r6w, r.c6w, cc(r.r6w));
    h += pCell(r.r6m, r.c6m, cc(r.r6m));
    h += pCell(r.r1y, r.c1y, cc(r.r1y));
    r.mom.forEach(v => { h += momCell(v); });
    h += '<td class="'+sc+'" style="text-align:center">'+(r.score>0?'+':'')+r.score+'</td>';
    h += '<td style="text-align:center;color:var(--muted)">'+r.momRank+'</td>';
    h += '<td style="text-align:center"><span class="badge '+m.c+'">'+m.l+'</span></td>';
    h += '</tr>';
  });
  return h;
}

// ── INDEX TABLE ───────────────────────────────────────────────────────────────
let sortKey='score', sortDir=-1;

function getFiltered() {
  const q  = document.getElementById('search').value.toLowerCase();
  const mf = document.getElementById('momFilter').value;
  return INDEX_DATA.filter(r => {
    if(q && !r.name.toLowerCase().includes(q)) return false;
    if(mf==='bull' && r.score<4)   return false;
    if(mf==='bear' && r.score>-4)  return false;
    if(mf==='ntrl' && (r.score>=4||r.score<=-4)) return false;
    return true;
  });
}

function renderTable() {
  const filtered = getFiltered();
  const sorted = [...filtered].sort((a,b) => {
    const av = a[sortKey]??-Infinity, bv = b[sortKey]??-Infinity;
    return typeof av==='string' ? sortDir*av.localeCompare(bv) : sortDir*(bv-av);
  });

  // ── Pinned watchlist row (always at top, not affected by sort/filter) ──────
  let h = '';
  if (WATCHLIST.length > 0) {
    const ws  = WATCHLIST.reduce((a,b)=>b.score>a.score?b:a, WATCHLIST[0]);
    const wsc = ws.score>0?'sa':ws.score<0?'sn':'s0';
    const wm  = getMom(ws.score);   // aggregate: use best-score stock as proxy
    // Compute watchlist-level aggregates for the row cells
    const wCur  = null;   // no single "price" for a basket
    const wR1w  = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r1w??0),0)/WATCHLIST.length) : null;
    const wR6m  = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r6m??0),0)/WATCHLIST.length) : null;
    const wR1y  = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r1y??0),0)/WATCHLIST.length) : null;
    const avgScore = Math.round(WATCHLIST.reduce((s,r)=>s+r.score,0)/WATCHLIST.length);
    const avgMom   = getMom(avgScore);
    const avgSc    = avgScore>0?'sa':avgScore<0?'sn':'s0';
    // Per-week average momentum signal
    const avgMomArr = Array.from({length:10}, (_,i) =>
      Math.round(WATCHLIST.reduce((s,r)=>s+(r.mom[i]??0),0)/WATCHLIST.length));

    h += '<tr class="watchlist-row">';
    h += '<td class="drill-link" data-index="__watchlist__" style="cursor:pointer;color:var(--accent);font-weight:600">'
       + WATCHLIST_KEY + ' <span style="font-size:10px;opacity:0.7">&#x2197;</span>'
       + ' <span style="font-size:10px;color:var(--muted);font-weight:400">('+WATCHLIST.length+' stocks, avg)</span></td>';
    h += '<td class="cur" style="color:var(--muted)">—</td>';
    const wR2w = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r2w??0),0)/WATCHLIST.length) : null;
    const wR3w = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r3w??0),0)/WATCHLIST.length) : null;
    const wR4w = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r4w??0),0)/WATCHLIST.length) : null;
    const wR5w = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r5w??0),0)/WATCHLIST.length) : null;
    const wR6w = WATCHLIST.length ? (WATCHLIST.reduce((s,r)=>s+(r.r6w??0),0)/WATCHLIST.length) : null;
    h += '<td class="'+cc(wR1w)+'">'+fp(wR1w)+'</td>';
    h += '<td class="'+cc(wR2w)+'">'+fp(wR2w)+'</td>';
    h += '<td class="'+cc(wR3w)+'">'+fp(wR3w)+'</td>';
    h += '<td class="'+cc(wR4w)+'">'+fp(wR4w)+'</td>';
    h += '<td class="'+cc(wR5w)+'">'+fp(wR5w)+'</td>';
    h += '<td class="'+cc(wR6w)+'">'+fp(wR6w)+'</td>';
    h += '<td class="'+cc(wR6m)+'">'+fp(wR6m)+'</td>';
    h += '<td class="'+cc(wR1y)+'">'+fp(wR1y)+'</td>';
    avgMomArr.forEach(v => { h += momCell(v); });
    h += '<td class="'+avgSc+'" style="text-align:center">'+(avgScore>0?'+':'')+avgScore+'</td>';
    h += '<td style="text-align:center;color:var(--muted)">—</td>';
    h += '<td style="text-align:center"><span class="badge '+avgMom.c+'">'+avgMom.l+'</span></td>';
    h += '</tr>';
    h += '<tr class="watchlist-sep"><td colspan="20"></td></tr>';
  }

  // ── Pinned lookup rows (amber, each individually removable) ──────────────
  if(lookupResults.length > 0) {
    lookupResults.forEach(r => {
      const m  = getMom(r.score);
      const sc = r.score>0?'sa':r.score<0?'sn':'s0';
      h += '<tr class="lookup-row">';
      h += '<td style="color:#fbbf24;font-weight:600">'
         + r.name
         + ' <span style="font-size:9px;background:rgba(251,191,36,0.2);color:#fbbf24;'
         + 'border:1px solid rgba(251,191,36,0.4);border-radius:4px;padding:1px 5px;'
         + 'font-family:var(--mono);font-weight:500;vertical-align:middle">LOOKUP</span>'
         + ' <span class="lookup-remove" onclick="removeLookupRow(\\'' + r.name + '\\')" title="Remove">&#x2715;</span>'
         + '</td>';
      h += '<td class="cur">'+fpr(r.cur)+'</td>';
      h += pCell(r.r1w, r.c1w, cc(r.r1w));
      h += pCell(r.r2w, r.c2w, cc(r.r2w));
      h += pCell(r.r3w, r.c3w, cc(r.r3w));
      h += pCell(r.r4w, r.c4w, cc(r.r4w));
      h += pCell(r.r5w, r.c5w, cc(r.r5w));
      h += pCell(r.r6w, r.c6w, cc(r.r6w));
      h += pCell(r.r6m, r.c6m, cc(r.r6m));
      h += pCell(r.r1y, r.c1y, cc(r.r1y));
      r.mom.forEach(v => { h += momCell(v); });
      h += '<td class="'+sc+'" style="text-align:center">'+(r.score>0?'+':'')+r.score+'</td>';
      h += '<td style="text-align:center;color:var(--muted)">'+r.momRank+'</td>';
      h += '<td style="text-align:center"><span class="badge '+m.c+'">'+m.l+'</span></td>';
      h += '</tr>';
    });
    h += '<tr class="lookup-sep"><td colspan="20"></td></tr>';
  }

  sorted.forEach(r => {
    const m  = getMom(r.score);
    const sc = r.score>0?'sa':r.score<0?'sn':'s0';
    const hasStocks = STOCK_DATA[r.name] && STOCK_DATA[r.name].length > 0;
    h += '<tr>';
    if(hasStocks) {
      h += '<td class="drill-link" data-index="'+r.name+'" style="cursor:pointer;color:var(--accent)">'+r.name+' <span style="font-size:10px;opacity:0.6">&#x2197;</span></td>';
    } else {
      h += '<td>'+r.name+'</td>';
    }
    h += '<td class="cur">'+fpr(r.cur)+'</td>';
    h += pCell(r.r1w, r.c1w, cc(r.r1w));
    h += pCell(r.r2w, r.c2w, cc(r.r2w));
    h += pCell(r.r3w, r.c3w, cc(r.r3w));
    h += pCell(r.r4w, r.c4w, cc(r.r4w));
    h += pCell(r.r5w, r.c5w, cc(r.r5w));
    h += pCell(r.r6w, r.c6w, cc(r.r6w));
    h += pCell(r.r6m, r.c6m, cc(r.r6m));
    h += pCell(r.r1y, r.c1y, cc(r.r1y));
    r.mom.forEach(v => { h += momCell(v); });
    h += '<td class="'+sc+'" style="text-align:center">'+(r.score>0?'+':'')+r.score+'</td>';
    h += '<td style="text-align:center;color:var(--muted)">'+r.momRank+'</td>';
    h += '<td style="text-align:center"><span class="badge '+m.c+'">'+m.l+'</span></td>';
    h += '</tr>';
  });
  document.getElementById('tbody').innerHTML = h ||
    '<tr><td colspan="20" style="text-align:center;padding:40px;color:var(--muted)">No indices match filter</td></tr>';

  const bull = INDEX_DATA.filter(r=>r.score>=4).length;
  const bear = INDEX_DATA.filter(r=>r.score<=-4).length;
  document.getElementById('s-total').textContent = INDEX_DATA.length;
  document.getElementById('s-bull').textContent  = bull;
  document.getElementById('s-bear').textContent  = bear;
  document.getElementById('s-neu').textContent   = INDEX_DATA.length-bull-bear;
  const best  = INDEX_DATA.reduce((a,b)=>(b.r1w??-Infinity)>(a.r1w??-Infinity)?b:a, INDEX_DATA[0]);
  const worst = INDEX_DATA.reduce((a,b)=>(b.r1w??Infinity)<(a.r1w??Infinity)?b:a, INDEX_DATA[0]);
  document.getElementById('s-best').textContent  = best  ? best.name.split(' ').pop()+' '+fp(best.r1w)  : '—';
  document.getElementById('s-worst').textContent = worst ? worst.name.split(' ').pop()+' '+fp(worst.r1w) : '—';
}

function sortBy(k) {
  document.querySelectorAll('th[id^="sh-"]').forEach(t=>t.classList.remove('sort-asc','sort-desc'));
  if(sortKey===k) sortDir*=-1; else { sortKey=k; sortDir=-1; }
  const el = document.getElementById('sh-'+k);
  if(el) el.classList.add(sortDir>0?'sort-asc':'sort-desc');
  renderTable();
}

// ── DRILL-DOWN ────────────────────────────────────────────────────────────────
let drillKey='score', drillDir=-1, currentIndex='';

function openDrill(indexName) {
  currentIndex = indexName;
  drillKey = 'score'; drillDir = -1;

  const isWatchlist = (indexName === '__watchlist__');
  const stocks = isWatchlist ? WATCHLIST : STOCK_DATA[indexName];
  const title  = isWatchlist ? WATCHLIST_KEY + ' — My Stocks' : indexName + ' — Constituent Stocks';

  document.getElementById('drillTitle').textContent = title;
  if(!stocks || stocks.length===0) {
    document.getElementById('drillBody').innerHTML =
      '<div class="no-data-msg">No stock data available for '+title+'.<br>Only indices with a defined constituent list support drill-down.</div>';
  } else {
    const bull = stocks.filter(r=>r.score>=4).length;
    const bear = stocks.filter(r=>r.score<=-4).length;
    document.getElementById('ds-total').textContent = stocks.length;
    document.getElementById('ds-bull').textContent  = bull;
    document.getElementById('ds-bear').textContent  = bear;
    document.getElementById('ds-neu').textContent   = stocks.length-bull-bear;
    const best  = stocks.reduce((a,b)=>(b.r1w??-Infinity)>(a.r1w??-Infinity)?b:a, stocks[0]);
    const worst = stocks.reduce((a,b)=>(b.r1w??Infinity)<(a.r1w??Infinity)?b:a, stocks[0]);
    document.getElementById('ds-best').textContent  = best  ? best.name+' '+fp(best.r1w)  : '—';
    document.getElementById('ds-worst').textContent = worst ? worst.name+' '+fp(worst.r1w) : '—';
    renderDrill();
  }
  fillHeaderDates(stocks, 'dhd-');
  document.getElementById('drillPanel').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeDrill() {
  document.getElementById('drillPanel').classList.remove('open');
  document.body.style.overflow = '';
}

function renderDrill() {
  const stocks = (currentIndex === '__watchlist__') ? WATCHLIST : (STOCK_DATA[currentIndex] || []);
  const sorted = [...stocks].sort((a,b) => {
    const av = a[drillKey]??-Infinity, bv = b[drillKey]??-Infinity;
    return typeof av==='string' ? drillDir*av.localeCompare(bv) : drillDir*(bv-av);
  });
  document.getElementById('drillBody').innerHTML = buildRows(sorted) ||
    '<tr><td colspan="20" style="text-align:center;padding:40px;color:var(--muted)">No data</td></tr>';
}

function sortDrill(k) {
  document.querySelectorAll('th[id^="dsh-"]').forEach(t=>t.classList.remove('sort-asc','sort-desc'));
  if(drillKey===k) drillDir*=-1; else { drillKey=k; drillDir=-1; }
  const el = document.getElementById('dsh-'+k);
  if(el) el.classList.add(drillDir>0?'sort-asc':'sort-desc');
  renderDrill();
}

document.addEventListener('keydown', e => { if(e.key==='Escape') closeDrill(); });
document.getElementById('tbody').addEventListener('click', e => {
  const td = e.target.closest('td.drill-link');
  if(td) openDrill(td.dataset.index);
});

// Fill period header dates from first data row
function fillHeaderDates(data, prefix) {
  if(!data || !data.length) return;
  const r = data[0];
  const map = {
    'cur': r.cur_dt,
    '1w': r.d1w, '2w': r.d2w, '3w': r.d3w,
    '4w': r.d4w, '5w': r.d5w, '6w': r.d6w,
    '6m': r.d6m, '1y': r.d1y
  };
  for(const [key, val] of Object.entries(map)) {
    const el = document.getElementById(prefix + key);
    if(el && val) el.textContent = fmtDate(val);
  }
}
fillHeaderDates(INDEX_DATA, 'hd-');

// Set tbl-wrap height so it fills exactly the remaining viewport
// This makes scroll happen inside tbl-wrap, so thead top:0 always works
(function setTableHeight() {
  function resize() {
    const wrap = document.querySelector('.tbl-wrap');
    const top  = document.querySelector('.sticky-top');
    if (!wrap || !top) return;
    const used = top.getBoundingClientRect().bottom;
    wrap.style.height = (window.innerHeight - used) + 'px';
  }
  resize();
  window.addEventListener('resize', resize);
})();

// ── RUNTIME STOCK LOOKUP ──────────────────────────────────────────────────────
// Auto-detects environment:
//   Local  → calls http://localhost:7777/lookup  (run: python lookup_server.py)
//   Netlify → calls /.netlify/functions/lookup   (deployed automatically)
const LOOKUP_PORT = 7777;
let lookupResults = [];

function getLookupUrl(tickersCsv) {
  const h = window.location.hostname;
  const isLocal = (h === 'localhost' || h === '127.0.0.1' || h === '' || window.location.protocol === 'file:');
  if (isLocal) {
    return 'http://localhost:' + LOOKUP_PORT + '/lookup?tickers=' + encodeURIComponent(tickersCsv);
  }
  return '/.netlify/functions/lookup?tickers=' + encodeURIComponent(tickersCsv);
}

async function runLookup() {
  const raw = document.getElementById('lookupInput').value.trim();
  if(!raw) return;

  const parts   = raw.replace(/[,\s]+/g, ',').split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
  const tickers = parts.map(t => (!t.startsWith('^') && !t.includes('.')) ? t + '.NS' : t);
  if(!tickers.length) return;

  const btn    = document.getElementById('lookupBtn');
  const status = document.getElementById('lookupStatus');
  btn.disabled = true;
  status.className = '';
  status.textContent = 'Fetching ' + tickers.length + ' ticker(s)\u2026';

  // Skip already-loaded tickers
  const existing = new Set(lookupResults.map(r => r._ticker));
  const toFetch  = tickers.filter(t => !existing.has(t));
  if(!toFetch.length) {
    status.textContent = 'Already loaded.';
    btn.disabled = false;
    return;
  }

  const isLocal = getLookupUrl('x').startsWith('http://localhost');
  try {
    const url  = getLookupUrl(toFetch.join(','));
    const resp = await fetch(url, {signal: AbortSignal.timeout(30000)});
    if(!resp.ok) throw new Error('Server returned ' + resp.status);
    const data = await resp.json();

    if(data.results && data.results.length) {
      data.results.forEach((r, i) => {
        r._ticker = toFetch[i] || (r.name + '.NS');
        r.momRank = i + 1;
      });
      lookupResults = [...lookupResults, ...data.results];
      renderTable();
      const errtxt = data.errors && data.errors.length ? ' \u00b7 failed: ' + data.errors.join(', ') : '';
      status.textContent = '\u2713 ' + data.results.length + ' stock(s) loaded' + errtxt;
    } else {
      status.className = 'err';
      status.textContent = 'No data returned. ' + (data.errors||[]).join(', ');
    }
  } catch(e) {
    status.className = 'err';
    const isFetchErr = e.name === 'TypeError' || (e.message||'').toLowerCase().includes('fetch');
    if(isLocal && isFetchErr) {
      status.textContent = '\u26a0 lookup_server.py not running \u2014 start it: python lookup_server.py';
    } else {
      status.textContent = 'Error: ' + e.message;
    }
  }
  btn.disabled = false;
}

function removeLookupRow(name) {
  lookupResults = lookupResults.filter(r => r.name !== name);
  if(!lookupResults.length) document.getElementById('lookupStatus').textContent = '';
  renderTable();
}

function clearAllLookups() {
  lookupResults = [];
  document.getElementById('lookupInput').value = '';
  document.getElementById('lookupStatus').textContent = '';
  renderTable();
}

document.getElementById('lookupInput').addEventListener('keydown', e => {
  if(e.key === 'Enter') runLookup();
});

renderTable();
"""

    html = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>NIFTY Dashboard \u2014 ' + as_of + '</title>\n'
        '<style>' + css + '</style>\n'
        '</head>\n<body>\n\n'

        '<div class="sticky-top">\n'
        '<div class="topbar">\n'
        '  <div>\n'
        '    <div class="brand">NIFTY INDEX DASHBOARD</div>\n'
        '    <div class="asof">As of ' + as_of + ' &nbsp;|&nbsp; Data: Yahoo Finance via yfinance &nbsp;|&nbsp; '
        'Click any <span style="color:var(--accent)">index name \u2197</span> to see constituent stocks</div>\n'
        '  </div>\n'
        '  <div style="font-family:var(--mono);font-size:11px;color:var(--muted)">Run nifty_refresh.py every Friday after 5 PM IST</div>\n'
        '</div>\n\n'

        '<div class="summary">\n'
        '  <div class="sc"><div class="sl">Indices</div><div class="sv" id="s-total">\u2014</div></div>\n'
        '  <div class="sc"><div class="sl">Bull</div><div class="sv pos" id="s-bull">\u2014</div></div>\n'
        '  <div class="sc"><div class="sl">Bear</div><div class="sv neg" id="s-bear">\u2014</div></div>\n'
        '  <div class="sc"><div class="sl">Neutral</div><div class="sv neu" id="s-neu">\u2014</div></div>\n'
        '  <div class="sc"><div class="sl">Best 1W</div><div class="sv pos" id="s-best">\u2014</div></div>\n'
        '  <div class="sc"><div class="sl">Worst 1W</div><div class="sv neg" id="s-worst">\u2014</div></div>\n'
        '</div>\n\n'

        '<div class="filters">\n'
        '  <label>Filter:</label>\n'
        '  <input type="text" id="search" placeholder="Search index..." oninput="renderTable()">\n'
        '  <label>Momentum:</label>\n'
        '  <select id="momFilter" onchange="renderTable()">\n'
        '    <option value="all">All</option>\n'
        '    <option value="bull">Bull only</option>\n'
        '    <option value="bear">Bear only</option>\n'
        '    <option value="ntrl">Neutral only</option>\n'
        '  </select>\n'
        '</div>\n\n'

        '<div class="lookup-bar">\n'
        '  <label>&#x1f50d; Lookup:</label>\n'
        '  <input type="text" id="lookupInput" placeholder="DIXON, ZOMATO, DMART  (comma-separated, Enter to fetch)">\n'
        '  <button class="lookup-btn" id="lookupBtn" onclick="runLookup()">Fetch Live</button>\n'
        '  <button class="lookup-clear-btn" onclick="clearAllLookups()">Clear</button>\n'
        '  <span id="lookupStatus"></span>\n'
        '  <span style="margin-left:auto;font-size:10px;color:var(--muted);font-family:var(--mono)">'
        'Local: <code style="color:#fbbf24">python lookup_server.py</code>'
        ' &nbsp;|&nbsp; Netlify: auto via serverless function</span>\n'
        '</div>\n\n'

        '<div class="notebar">Weekly closes (Friday) &nbsp;|&nbsp; Momentum = +1/\u22121 per week over 10 weeks'
        ' &nbsp;|&nbsp; Score = sum &nbsp;|&nbsp; Bull \u2265 +4 &nbsp;|&nbsp; Bear \u2264 \u22124'
        ' &nbsp;|&nbsp; Click <span style="color:var(--accent)">index name</span> to drill into stocks</div>\n'
'</div>\n\n'

        '<div class="tbl-wrap">\n'
        '<table>\n<thead>\n<tr>\n'
        '  <th onclick="sortBy(\'name\')" id="sh-name">Index</th>\n'
        '  <th onclick="sortBy(\'cur\')">Current<br><span class="hdr-date" id="hd-cur"></span></th>\n'
        '  <th onclick="sortBy(\'r1w\')" id="sh-r1w" class="sort-desc">1W %<br><span class="hdr-date" id="hd-1w"></span></th>\n'
        '  <th onclick="sortBy(\'r2w\')" id="sh-r2w">2W %<br><span class="hdr-date" id="hd-2w"></span></th>\n'
        '  <th onclick="sortBy(\'r3w\')" id="sh-r3w">3W %<br><span class="hdr-date" id="hd-3w"></span></th>\n'
        '  <th onclick="sortBy(\'r4w\')" id="sh-r4w">4W %<br><span class="hdr-date" id="hd-4w"></span></th>\n'
        '  <th onclick="sortBy(\'r5w\')" id="sh-r5w">5W %<br><span class="hdr-date" id="hd-5w"></span></th>\n'
        '  <th onclick="sortBy(\'r6w\')" id="sh-r6w">6W %<br><span class="hdr-date" id="hd-6w"></span></th>\n'
        '  <th onclick="sortBy(\'r6m\')" id="sh-r6m">6M %<br><span class="hdr-date" id="hd-6m"></span></th>\n'
        '  <th onclick="sortBy(\'r1y\')" id="sh-r1y">1Y %<br><span class="hdr-date" id="hd-1y"></span></th>\n'
        '  <th>W10</th><th>W9</th><th>W8</th><th>W7</th><th>W6</th>\n'
        '  <th>W5</th><th>W4</th><th>W3</th><th>W2</th><th>W1</th>\n'
        '  <th onclick="sortBy(\'score\')" id="sh-score">Score</th>\n'
        '  <th>Rank</th>\n'
        '  <th>Momentum</th>\n'
        '</tr>\n</thead>\n'
        '<tbody id="tbody"></tbody>\n'
        '</table>\n</div>\n\n'

        '<div class="legend">\n'
        '  <span class="pos">+ green = positive</span>\n'
        '  <span class="neg">- red = negative</span>\n'
        '  <span><span class="badge bull">Bull</span> \u2265 +4</span>\n'
        '  <span><span class="badge ntrl">Neutral</span> \u22123 to +3</span>\n'
        '  <span><span class="badge bear">Bear</span> \u2264 \u22124</span>\n'
        '  <span style="margin-left:auto;color:var(--muted);font-family:var(--mono);font-size:11px">'
        'Click <span style="color:var(--accent)">index name \u2197</span> \u2192 stock drill-down &nbsp;|&nbsp; Click column header \u2192 sort</span>\n'
        '</div>\n\n'

        '<!-- DRILL-DOWN PANEL -->\n'
        '<div class="drill-panel" id="drillPanel">\n'
        '  <div class="drill-header">\n'
        '    <div>\n'
        '      <div class="drill-title" id="drillTitle">\u2014</div>\n'
        '      <div class="drill-sub">Constituent stocks \u2014 same momentum metrics as index view</div>\n'
        '    </div>\n'
        '    <button class="close-btn" onclick="closeDrill()">\u2715 Close &nbsp;(Esc)</button>\n'
        '  </div>\n'
        '  <div class="drill-summary">\n'
        '    <div class="sc"><div class="sl">Stocks</div><div class="sv" id="ds-total">\u2014</div></div>\n'
        '    <div class="sc"><div class="sl">Bull</div><div class="sv pos" id="ds-bull">\u2014</div></div>\n'
        '    <div class="sc"><div class="sl">Bear</div><div class="sv neg" id="ds-bear">\u2014</div></div>\n'
        '    <div class="sc"><div class="sl">Neutral</div><div class="sv neu" id="ds-neu">\u2014</div></div>\n'
        '    <div class="sc"><div class="sl">Best 1W</div><div class="sv pos" id="ds-best">\u2014</div></div>\n'
        '    <div class="sc"><div class="sl">Worst 1W</div><div class="sv neg" id="ds-worst">\u2014</div></div>\n'
        '  </div>\n'
        '  <div class="drill-notebar">Sorted by momentum score (highest first) \u2014 click headers to re-sort \u2014 press Esc to close</div>\n'
        '  <div class="drill-body">\n'
        '    <div class="tbl-wrap">\n'
        '    <table id="drillTable">\n<thead>\n<tr>\n'
        '      <th onclick="sortDrill(\'name\')" id="dsh-name">Stock</th>\n'
        '      <th onclick="sortDrill(\'cur\')">Price (\u20b9)<br><span class="hdr-date" id="dhd-cur"></span></th>\n'
        '      <th onclick="sortDrill(\'r1w\')" id="dsh-r1w" class="sort-desc">1W %<br><span class="hdr-date" id="dhd-1w"></span></th>\n'
        '      <th onclick="sortDrill(\'r2w\')" id="dsh-r2w">2W %<br><span class="hdr-date" id="dhd-2w"></span></th>\n'
        '      <th onclick="sortDrill(\'r3w\')" id="dsh-r3w">3W %<br><span class="hdr-date" id="dhd-3w"></span></th>\n'
        '      <th onclick="sortDrill(\'r4w\')" id="dsh-r4w">4W %<br><span class="hdr-date" id="dhd-4w"></span></th>\n'
        '      <th onclick="sortDrill(\'r5w\')" id="dsh-r5w">5W %<br><span class="hdr-date" id="dhd-5w"></span></th>\n'
        '      <th onclick="sortDrill(\'r6w\')" id="dsh-r6w">6W %<br><span class="hdr-date" id="dhd-6w"></span></th>\n'
        '      <th onclick="sortDrill(\'r6m\')" id="dsh-r6m">6M %<br><span class="hdr-date" id="dhd-6m"></span></th>\n'
        '      <th onclick="sortDrill(\'r1y\')" id="dsh-r1y">1Y %<br><span class="hdr-date" id="dhd-1y"></span></th>\n'
        '      <th>W10</th><th>W9</th><th>W8</th><th>W7</th><th>W6</th>\n'
        '      <th>W5</th><th>W4</th><th>W3</th><th>W2</th><th>W1</th>\n'
        '      <th onclick="sortDrill(\'score\')" id="dsh-score">Score</th>\n'
        '      <th>Rank</th>\n'
        '      <th>Momentum</th>\n'
        '    </tr>\n</thead>\n'
        '    <tbody id="drillBody"></tbody>\n'
        '    </table>\n    </div>\n  </div>\n</div>\n\n'
        '<script>\n' + js + '\n</script>\n'
        '</body>\n</html>'
    )
    return html

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 62)
    print("  NIFTY Index Dashboard — Weekly Refresh")
    print(f"  {datetime.now().strftime('%A, %d %b %Y  %I:%M %p')}")
    print("=" * 62)

    print("\n[1/4] Fetching NIFTY index data...\n")
    idx_df = fetch_indices()
    if idx_df.empty:
        print("No index data fetched. Check internet connection.")
        sys.exit(1)
    idx_df.to_csv(CSV_INDEX_PATH, index=False)
    print(f"\n  Saved \u2192 {CSV_INDEX_PATH}")

    print("\n[2/4] Fetching constituent stock data...")
    stk_df = fetch_stocks()
    if not stk_df.empty:
        stk_df.to_csv(CSV_STOCKS_PATH, index=False)
        print(f"\n  Saved \u2192 {CSV_STOCKS_PATH}")

    wl_tickers = load_watchlist()
    wl_df      = pd.DataFrame()
    if wl_tickers:
        print(f"\n[2b] Fetching watchlist ({len(wl_tickers)} stocks from stocks.txt)...")
        wl_df = fetch_watchlist(wl_tickers)
        if not wl_df.empty:
            wl_df.to_csv(CSV_WATCHLIST_PATH, index=False)
            print(f"\n  Saved \u2192 {CSV_WATCHLIST_PATH}")
    else:
        print("\n[2b] No stocks.txt found (or empty) — skipping watchlist.")
        print(f"       Create {WATCHLIST_FILE} with one ticker per line to enable this feature.")

    print("\n[3/4] Computing returns and momentum signals...")
    index_stats = compute_stats(idx_df, name_col="index_name")
    print(f"  {len(index_stats)} indices ready")
    stock_stats = {}
    if not stk_df.empty:
        stock_stats = compute_stock_stats(stk_df)
        total_stks = sum(len(v) for v in stock_stats.values())
        print(f"  {total_stks} stocks across {len(stock_stats)} indices ready")
    watchlist_stats = []
    if not wl_df.empty:
        watchlist_stats = compute_stats(wl_df, name_col="stock_name")
        print(f"  {len(watchlist_stats)} watchlist stocks ready")

    print("\n[4/4] Generating dashboard HTML...")
    as_of = datetime.now().strftime("%d %b %Y, %I:%M %p IST")
    html  = generate_html(index_stats, stock_stats, watchlist_stats, as_of)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved \u2192 {HTML_PATH}")

    write_lookup_server()
    write_netlify_function()
    write_netlify_toml()
    write_package_json()

    # ── Auto-launch lookup_server.py in the background ────────────────────
    import subprocess, socket as _sock
    already_up = False
    try:
        with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
            already_up = (s.connect_ex(("localhost", 7777)) == 0)
    except Exception:
        pass

    if already_up:
        print("\n  Lookup server already running on port 7777 — no restart needed.")
    else:
        try:
            proc = subprocess.Popen(
                [sys.executable, LOOKUP_SERVER_PATH],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,   # detach: outlives this script
            )
            print(f"\n  Lookup server started \u2192 PID {proc.pid}  (port 7777)")
            if sys.platform == "win32":
                print(f"  To stop: taskkill /F /PID {proc.pid}")
            else:
                print(f"  To stop: kill {proc.pid}")
        except Exception as e:
            print(f"\n  Could not auto-start lookup_server.py: {e}")
            print("  Start it manually in a separate terminal: python lookup_server.py")

    # webbrowser.open(f"file://{HTML_PATH}")
    print("\nDone! Click any index name (in accent colour \u2197) to see its constituent stocks.")
    print("Netlify: push to git \u2192 serverless function deploys automatically.")
    print("Run again next Friday after 5 PM IST.")
    print("=" * 62)

if __name__ == "__main__":
    main()

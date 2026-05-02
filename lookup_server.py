"""
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
    print("Press Ctrl+C to stop.\n")
    try:
        HTTPServer(("localhost", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)

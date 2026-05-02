// netlify/functions/lookup.js
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

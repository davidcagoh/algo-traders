#!/usr/bin/env python3
"""
Paper-trade the signed mean-variance portfolio with a local live dashboard.

The bot never places exchange orders. It pulls Hyperliquid market data, maintains
paper perp positions, applies taker fees and funding, and exposes a dashboard.

Run from the repository root:
  freqtrade-experiment/research/.venv/bin/python \
    freqtrade-experiment/mean-variance-paper/local_dashboard.py
"""
from __future__ import annotations

import argparse
import json
import math
import socket
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests

EXPERIMENT = Path(__file__).resolve().parents[1]
RESEARCH = EXPERIMENT / "research"
sys.path.insert(0, str(RESEARCH / "analysis"))

from run_portfolio_baselines import load_universe
from run_portfolio_short_funding import target_weights


UNIVERSE_JSON = RESEARCH / "analysis" / "reports" / "universe_selection_hl_1h_current.json"
FUNDING_DIR = RESEARCH / "data" / "hyperliquid" / "funding"
STATE_DIR = Path(__file__).resolve().parent / "state"
STATE_PATH = STATE_DIR / "signed_mv_state.json"
LOG_PATH = STATE_DIR / "signed_mv.log"
API_URL = "https://api.hyperliquid.xyz/info"
INTERVAL_MS = {"1h": 3_600_000}
MAX_CANDLES = 5000


def as_utc_ns(values: Any) -> Any:
    converted = pd.to_datetime(values, utc=True)
    if isinstance(converted, pd.Series):
        return converted.dt.as_unit("ns")
    if isinstance(converted, pd.DatetimeIndex):
        return converted.as_unit("ns")
    return converted


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Signed MV Paper Trading</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --line: #d9dee7;
      --text: #17202a;
      --muted: #647083;
      --green: #15803d;
      --red: #b91c1c;
      --blue: #1d4ed8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    h1 { margin: 0; font-size: 18px; font-weight: 650; }
    button {
      border: 1px solid var(--line);
      background: #fff;
      padding: 8px 10px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }
    button.primary { background: var(--text); color: white; border-color: var(--text); }
    main { padding: 16px; display: grid; gap: 14px; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(8, minmax(120px, 1fr));
      gap: 10px;
    }
    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .metric { padding: 10px; }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 20px; font-weight: 700; margin-top: 3px; }
    .panel { padding: 12px; min-width: 0; }
    .grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(360px, .8fr); gap: 14px; }
    canvas { width: 100%; height: 280px; display: block; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--line); padding: 7px 6px; text-align: right; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-weight: 650; }
    .pos { color: var(--green); }
    .neg { color: var(--red); }
    .status { display: flex; gap: 8px; align-items: center; color: var(--muted); font-size: 13px; }
    .dot { width: 9px; height: 9px; border-radius: 999px; background: #999; }
    .dot.ok { background: var(--green); }
    .dot.bad { background: var(--red); }
    .log { max-height: 220px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: #2d3748; }
    @media (max-width: 1100px) {
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Signed Mean-Variance Paper Trading</h1>
      <div class="status"><span id="dot" class="dot"></span><span id="status">Loading</span></div>
    </div>
    <div>
      <button onclick="post('/api/update')">Update</button>
      <button class="primary" onclick="post('/api/rebalance')">Rebalance</button>
    </div>
  </header>
  <main>
    <section class="metrics" id="metrics"></section>
    <section class="grid">
      <div class="panel"><canvas id="equity"></canvas></div>
      <div class="panel"><canvas id="weights"></canvas></div>
    </section>
    <section class="grid">
      <div class="panel">
        <table id="positions"></table>
      </div>
      <div class="panel">
        <table id="targets"></table>
      </div>
    </section>
    <section class="panel">
      <div class="log" id="log"></div>
    </section>
  </main>
  <script>
    const fmt = new Intl.NumberFormat(undefined, {maximumFractionDigits: 2});
    const pct = x => Number.isFinite(x) ? `${(x * 100).toFixed(2)}%` : 'n/a';
    const money = x => Number.isFinite(x) ? `$${fmt.format(x)}` : 'n/a';
    function cls(x) { return x > 0 ? 'pos' : x < 0 ? 'neg' : ''; }
    async function post(path) {
      await fetch(path, {method: 'POST'});
      await refresh();
    }
    function metric(label, value, klass='') {
      return `<div class="metric"><div class="label">${label}</div><div class="value ${klass}">${value}</div></div>`;
    }
    function timeLabel(ts) {
      const d = new Date(ts);
      return d.toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
    }
    function drawLine(canvas, points) {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
      const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
      const w = rect.width, h = rect.height, leftPad = 46, rightPad = 46, topPad = 34, bottomPad = 48;
      const plotW = w - leftPad - rightPad;
      const plotH = h - topPad - bottomPad;
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = '#d9dee7'; ctx.lineWidth = 1;
      for (let i=0;i<5;i++) {
        const y = topPad + i * plotH / 4;
        ctx.beginPath(); ctx.moveTo(leftPad, y); ctx.lineTo(w - rightPad, y); ctx.stroke();
      }
      if (!points.length) return;
      const vals = points.map(p => p.equity);
      const min = Math.min(...vals), max = Math.max(...vals);
      const span = Math.max(max - min, 1e-9);
      ctx.strokeStyle = '#1d4ed8'; ctx.lineWidth = 2;
      ctx.beginPath();
      points.forEach((p, i) => {
        const x = leftPad + i * plotW / Math.max(points.length - 1, 1);
        const y = topPad + plotH - (p.equity - min) / span * plotH;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.strokeStyle = '#9aa3af'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(leftPad, topPad + plotH); ctx.lineTo(w - rightPad, topPad + plotH); ctx.stroke();
      ctx.fillStyle = '#17202a'; ctx.font = '12px sans-serif';
      const pnl = vals[vals.length - 1] - vals[0];
      ctx.fillText(`Equity ${money(vals[vals.length-1])}  PnL ${money(pnl)}`, leftPad, 18);
      ctx.fillStyle = '#647083';
      ctx.fillText(`${money(min)} - ${money(max)}`, leftPad, topPad + plotH + 16);
      const ticks = points.length === 1 ? [0] : [0, Math.floor((points.length - 1) / 2), points.length - 1];
      [...new Set(ticks)].forEach((i, tickIndex, labels) => {
        const x = leftPad + i * plotW / Math.max(points.length - 1, 1);
        ctx.textAlign = tickIndex === 0 ? 'left' : tickIndex === labels.length - 1 ? 'right' : 'center';
        ctx.fillText(timeLabel(points[i].ts), x, h - 8);
      });
      ctx.textAlign = 'left';
    }
    function drawBars(canvas, rows) {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
      const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
      const w = rect.width, h = rect.height, pad = 32;
      ctx.clearRect(0, 0, w, h);
      const maxAbs = Math.max(.2, ...rows.map(r => Math.abs(r.weight)));
      const zero = h / 2;
      ctx.strokeStyle = '#17202a'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pad, zero); ctx.lineTo(w - pad, zero); ctx.stroke();
      const bw = (w - 2*pad) / rows.length * .72;
      rows.forEach((r, i) => {
        const x = pad + i * (w - 2*pad) / rows.length + bw * .2;
        const y = zero - r.weight / maxAbs * (h/2 - pad);
        ctx.fillStyle = r.weight >= 0 ? '#15803d' : '#b91c1c';
        ctx.fillRect(x, Math.min(y, zero), bw, Math.abs(y - zero));
        ctx.fillStyle = '#17202a'; ctx.font = '11px sans-serif';
        ctx.save(); ctx.translate(x + bw/2, h - 8); ctx.rotate(-Math.PI/5); ctx.fillText(r.coin, -10, 0); ctx.restore();
      });
      ctx.fillStyle = '#17202a'; ctx.font = '12px sans-serif'; ctx.fillText('Current weights', pad, 18);
    }
    async function refresh() {
      const res = await fetch('/api/status');
      const s = await res.json();
      document.getElementById('dot').className = `dot ${s.health.ok ? 'ok' : 'bad'}`;
      document.getElementById('status').textContent = s.health.message;
      const stats = s.stats;
      document.getElementById('metrics').innerHTML = [
        metric('Equity', money(stats.equity), cls(stats.total_return)),
        metric('Return', pct(stats.total_return), cls(stats.total_return)),
        metric('Drawdown', pct(stats.drawdown), cls(-stats.drawdown)),
      metric('Sharpe', Number.isFinite(stats.sharpe) ? fmt.format(stats.sharpe) : 'n/a', cls(stats.sharpe)),
        metric('Gross', pct(stats.gross_exposure)),
        metric('Net', pct(stats.net_exposure), cls(stats.net_exposure)),
        metric('Fees', money(stats.total_fees), 'neg'),
        metric('Funding', money(stats.total_funding), cls(stats.total_funding)),
      ].join('');
      const rows = Object.entries(s.positions).map(([coin, p]) => ({coin, ...p}));
      document.getElementById('positions').innerHTML = `<tr><th>Coin</th><th>Qty</th><th>Weight</th><th>Target</th><th>Price</th><th>UPnL</th></tr>` +
        rows.map(r => `<tr><td>${r.coin}</td><td>${fmt.format(r.qty)}</td><td class="${cls(r.weight)}">${pct(r.weight)}</td><td class="${cls(r.target_weight)}">${pct(r.target_weight)}</td><td>${fmt.format(r.price)}</td><td class="${cls(r.unrealized_pnl)}">${money(r.unrealized_pnl)}</td></tr>`).join('');
      document.getElementById('targets').innerHTML = `<tr><th>Field</th><th>Value</th></tr>` +
        Object.entries(s.config).map(([k,v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('') +
        `<tr><td>last rebalance</td><td>${s.last_rebalance || 'never'}</td></tr>` +
        `<tr><td>next rebalance</td><td>${s.next_rebalance_due || 'n/a'}</td></tr>` +
        `<tr><td>last update</td><td>${s.last_update || 'never'}</td></tr>`;
      document.getElementById('log').textContent = s.logs.join('\n');
      drawLine(document.getElementById('equity'), s.equity_history);
      drawBars(document.getElementById('weights'), rows);
    }
    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


class LocalHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self) -> None:
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.server_name = str(self.server_address[0])
        self.server_port = int(self.server_address[1])


class PaperBot:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.lock = threading.RLock()
        self.universe = load_universe(args.universe_json)
        self.state_path = args.state_path
        self.session = requests.Session()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self.load_state()

    def log(self, message: str) -> None:
        line = f"{datetime.now(UTC).isoformat(timespec='seconds')} {message}"
        with self.lock:
            self.state.setdefault("logs", []).append(line)
            self.state["logs"] = self.state["logs"][-200:]
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a") as handle:
                handle.write(line + "\n")

    def load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            if state.get("version", 1) < 2:
                state["logs"] = [
                    line
                    for line in state.get("logs", [])
                    if "Out of bounds nanosecond timestamp" not in line
                ]
                state["version"] = 2
            return state
        now = datetime.now(UTC).isoformat()
        return {
            "version": 2,
            "started_at": now,
            "last_update": None,
            "last_rebalance": None,
            "cash": float(self.args.initial_equity),
            "initial_equity": float(self.args.initial_equity),
            "positions": {
                coin: {"qty": 0.0, "entry_price": 0.0, "realized_pnl": 0.0}
                for coin in self.universe
            },
            "last_prices": {},
            "last_funding_time_ms": self.latest_local_funding_times(),
            "target_weights": {coin: 0.0 for coin in self.universe},
            "equity_history": [],
            "trades": [],
            "funding_events": [],
            "logs": [],
        }

    def save(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2))
        tmp.replace(self.state_path)

    def post_info(self, payload: dict[str, Any], timeout: float = 20.0) -> Any:
        response = self.session.post(API_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def latest_local_funding_times(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for coin in self.universe:
            path = FUNDING_DIR / f"{coin}-funding.parquet"
            if not path.exists():
                out[coin] = int(time.time() * 1000)
                continue
            df = pd.read_parquet(path, columns=["time"])
            if df.empty:
                out[coin] = int(time.time() * 1000)
            else:
                out[coin] = int(as_utc_ns(df["time"]).max().timestamp() * 1000)
        return out

    def fetch_mids(self) -> dict[str, float]:
        data = self.post_info({"type": "allMids"}, timeout=10)
        return {coin: float(data[coin]) for coin in self.universe if coin in data}

    def fetch_candles(self, coin: str) -> pd.DataFrame:
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - INTERVAL_MS["1h"] * MAX_CANDLES
        data = self.post_info(
            {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": "1h",
                    "startTime": start_ms,
                    "endTime": end_ms,
                },
            },
            timeout=30,
        )
        if not isinstance(data, list) or not data:
            raise RuntimeError(f"No candle data for {coin}")
        df = pd.DataFrame(data).rename(columns={"t": "date", "c": "close"})
        df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True).dt.as_unit("ns")
        df["close"] = df["close"].astype(float)
        return df[["date", "close"]].sort_values("date").drop_duplicates("date")

    def funding_daily(self, index: pd.DatetimeIndex) -> pd.DataFrame:
        series = []
        for coin in self.universe:
            path = FUNDING_DIR / f"{coin}-funding.parquet"
            if path.exists():
                df = pd.read_parquet(path)
                df["time"] = as_utc_ns(df["time"])
                daily = df.set_index("time")["funding_rate"].resample("1D").sum()
                daily.index = daily.index.as_unit("ns")
            else:
                daily = pd.Series(0.0, index=index)
            series.append(daily.rename(coin))
        return pd.concat(series, axis=1).reindex(as_utc_ns(index)).fillna(0.0)

    def compute_target(self) -> dict[str, float]:
        closes = []
        for coin in self.universe:
            closes.append(
                self.fetch_candles(coin).set_index("date")["close"].resample("1D").last().dropna().rename(coin)
            )
            time.sleep(self.args.api_pause)
        prices = pd.concat(closes, axis=1).dropna(how="any")
        price_returns = prices.pct_change().dropna()
        funding = self.funding_daily(price_returns.index)
        hist = (price_returns - funding).tail(self.args.lookback_days)
        if len(hist) < self.args.lookback_days:
            raise RuntimeError(f"Only {len(hist)} daily observations, need {self.args.lookback_days}")
        equity = self.mark_equity(self.state["last_prices"] or self.fetch_mids())
        previous = self.current_weights(self.state["last_prices"] or self.fetch_mids(), equity)
        weights = target_weights(
            "shrunk_mean_variance_signed",
            hist,
            previous,
            self.args.max_abs_weight,
            self.args.gross_limit,
            self.args.mean_shrink,
            self.args.risk_aversion,
            self.args.turnover_penalty,
        )
        return {coin: float(weight) for coin, weight in zip(self.universe, weights, strict=True)}

    def mark_equity(self, prices: dict[str, float]) -> float:
        equity = float(self.state["cash"])
        for coin, position in self.state["positions"].items():
            qty = float(position["qty"])
            if abs(qty) <= 1e-12:
                continue
            price = prices.get(coin)
            if price is None:
                continue
            equity += qty * (price - float(position["entry_price"]))
        return equity

    def current_weights(self, prices: dict[str, float], equity: float) -> np.ndarray:
        if equity <= 0:
            return np.zeros(len(self.universe))
        weights = []
        for coin in self.universe:
            qty = float(self.state["positions"][coin]["qty"])
            weights.append(qty * prices.get(coin, 0.0) / equity)
        return np.asarray(weights, dtype=float)

    def trade_to_targets(self, prices: dict[str, float], targets: dict[str, float], reason: str) -> None:
        equity = self.mark_equity(prices)
        if equity <= 0:
            raise RuntimeError("Equity <= 0")
        total_fee = 0.0
        for coin in self.universe:
            price = prices[coin]
            desired_qty = targets.get(coin, 0.0) * equity / price
            position = self.state["positions"][coin]
            old_qty = float(position["qty"])
            delta = desired_qty - old_qty
            if abs(delta * price) < self.args.min_trade_notional:
                continue
            fee = abs(delta * price) * self.args.fee
            self.state["cash"] -= fee
            total_fee += fee
            self.update_position_for_trade(coin, delta, price)
            self.state["trades"].append(
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "coin": coin,
                    "delta_qty": delta,
                    "price": price,
                    "notional": delta * price,
                    "fee": fee,
                    "reason": reason,
                }
            )
        self.state["trades"] = self.state["trades"][-500:]
        self.state["last_rebalance"] = datetime.now(UTC).isoformat()
        if total_fee:
            self.log(f"rebalance {reason}: fees={total_fee:.4f}")

    def update_position_for_trade(self, coin: str, delta: float, price: float) -> None:
        position = self.state["positions"][coin]
        old_qty = float(position["qty"])
        old_entry = float(position["entry_price"])
        if abs(old_qty) <= 1e-12:
            position["qty"] = delta
            position["entry_price"] = price if abs(delta) > 1e-12 else 0.0
            return
        if old_qty * delta >= 0:
            new_qty = old_qty + delta
            position["entry_price"] = (
                (abs(old_qty) * old_entry + abs(delta) * price) / max(abs(new_qty), 1e-12)
                if abs(new_qty) > 1e-12
                else 0.0
            )
            position["qty"] = new_qty
            return
        close_qty = min(abs(delta), abs(old_qty))
        realized = close_qty * math.copysign(1.0, old_qty) * (price - old_entry)
        self.state["cash"] += realized
        position["realized_pnl"] = float(position.get("realized_pnl", 0.0)) + realized
        new_qty = old_qty + delta
        position["qty"] = new_qty
        position["entry_price"] = price if old_qty * new_qty < 0 else (old_entry if abs(new_qty) > 1e-12 else 0.0)

    def fetch_funding_since(self, coin: str, start_ms: int) -> list[dict[str, Any]]:
        now_ms = int(time.time() * 1000)
        if start_ms >= now_ms - 60_000:
            return []
        data = self.post_info(
            {
                "type": "fundingHistory",
                "coin": coin,
                "startTime": start_ms + 1,
                "endTime": now_ms,
            },
            timeout=20,
        )
        if not isinstance(data, list):
            return []
        return data

    def apply_new_funding(self, prices: dict[str, float]) -> None:
        for coin in self.universe:
            last_ms = int(self.state["last_funding_time_ms"].get(coin, int(time.time() * 1000)))
            try:
                records = self.fetch_funding_since(coin, last_ms)
            except Exception as exc:
                self.log(f"funding fetch failed {coin}: {exc}")
                continue
            qty = float(self.state["positions"][coin]["qty"])
            for record in records:
                ts = int(record["time"])
                rate = float(record["fundingRate"])
                pnl = -qty * prices.get(coin, 0.0) * rate
                self.state["cash"] += pnl
                self.state["funding_events"].append(
                    {"ts": ts, "coin": coin, "rate": rate, "qty": qty, "pnl": pnl}
                )
                self.state["last_funding_time_ms"][coin] = max(ts, self.state["last_funding_time_ms"].get(coin, 0))
            if records:
                self.state["funding_events"] = self.state["funding_events"][-500:]
                self.log(f"applied {len(records)} funding records for {coin}")
            time.sleep(self.args.api_pause)

    def maybe_rebalance(self, prices: dict[str, float]) -> None:
        last = self.state.get("last_rebalance")
        due = last is None
        if last is not None:
            due = datetime.fromisoformat(last) + timedelta(days=self.args.rebalance_days) <= datetime.now(UTC)
        if not due:
            return
        targets = self.compute_target()
        self.state["target_weights"] = targets
        self.trade_to_targets(prices, targets, "scheduled")

    def update_once(self, force_rebalance: bool = False) -> None:
        with self.lock:
            prices = self.fetch_mids()
            missing = [coin for coin in self.universe if coin not in prices]
            if missing:
                raise RuntimeError(f"Missing prices: {missing}")
            self.state["last_prices"] = prices
            self.apply_new_funding(prices)
            if force_rebalance:
                targets = self.compute_target()
                self.state["target_weights"] = targets
                self.trade_to_targets(prices, targets, "manual")
            else:
                self.maybe_rebalance(prices)
            equity = self.mark_equity(prices)
            weights = self.current_weights(prices, equity)
            gross = float(np.abs(weights).sum())
            net = float(weights.sum())
            peak = max([row["equity"] for row in self.state["equity_history"]] + [equity])
            history_row = {
                "ts": datetime.now(UTC).isoformat(),
                "equity": equity,
                "cash": float(self.state["cash"]),
                "gross": gross,
                "net": net,
                "drawdown": equity / peak - 1.0 if peak else 0.0,
            }
            self.state["equity_history"].append(history_row)
            self.state["equity_history"] = self.state["equity_history"][-5000:]
            self.state["last_update"] = datetime.now(UTC).isoformat()
            self.save()

    def run_loop(self) -> None:
        while True:
            try:
                self.update_once(False)
            except Exception as exc:
                self.log(f"update failed: {exc}")
                self.save()
            time.sleep(self.args.update_seconds)

    def status(self) -> dict[str, Any]:
        with self.lock:
            prices = self.state.get("last_prices") or {}
            equity = self.mark_equity(prices) if prices else float(self.state["cash"])
            weights = self.current_weights(prices, equity) if prices else np.zeros(len(self.universe))
            peak = max([row["equity"] for row in self.state["equity_history"]] + [equity])
            returns = pd.Series([row["equity"] for row in self.state["equity_history"]], dtype=float).pct_change().dropna()
            sharpe = (
                float(returns.mean() / returns.std() * math.sqrt(365 * 24 * 60 * 60 / self.args.update_seconds))
                if len(returns) >= 30 and returns.std() > 0
                else None
            )
            total_fees = sum(abs(trade["fee"]) for trade in self.state.get("trades", []))
            total_funding = sum(event["pnl"] for event in self.state.get("funding_events", []))
            positions = {}
            for i, coin in enumerate(self.universe):
                position = self.state["positions"][coin]
                qty = float(position["qty"])
                price = float(prices.get(coin, 0.0))
                entry = float(position["entry_price"])
                positions[coin] = {
                    "qty": qty,
                    "entry_price": entry,
                    "price": price,
                    "weight": float(weights[i]) if i < len(weights) else 0.0,
                    "target_weight": float(self.state.get("target_weights", {}).get(coin, 0.0)),
                    "unrealized_pnl": qty * (price - entry) if price else 0.0,
                }
            last_rebalance = self.state.get("last_rebalance")
            next_due = None
            if last_rebalance:
                next_due = (datetime.fromisoformat(last_rebalance) + timedelta(days=self.args.rebalance_days)).isoformat()
            stale = self.state.get("last_update") is None
            if self.state.get("last_update"):
                stale = datetime.fromisoformat(self.state["last_update"]) < datetime.now(UTC) - timedelta(seconds=self.args.update_seconds * 3)
            return {
                "health": {
                    "ok": not stale,
                    "message": "ok" if not stale else "stale or starting",
                },
                "config": {
                    "strategy": "signed_mean_variance",
                    "lookback_days": self.args.lookback_days,
                    "rebalance_days": self.args.rebalance_days,
                    "mean_shrink": self.args.mean_shrink,
                    "risk_aversion": self.args.risk_aversion,
                    "max_abs_weight": self.args.max_abs_weight,
                    "gross_limit": self.args.gross_limit,
                },
                "stats": {
                    "equity": equity,
                    "total_return": equity / float(self.state["initial_equity"]) - 1.0,
                    "drawdown": equity / peak - 1.0 if peak else 0.0,
                    "sharpe": sharpe,
                    "gross_exposure": float(np.abs(weights).sum()),
                    "net_exposure": float(weights.sum()),
                    "total_fees": total_fees,
                    "total_funding": total_funding,
                },
                "positions": positions,
                "equity_history": self.state["equity_history"][-1000:],
                "last_update": self.state.get("last_update"),
                "last_rebalance": last_rebalance,
                "next_rebalance_due": next_due,
                "logs": self.state.get("logs", [])[-80:],
            }


def make_handler(bot: PaperBot) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, payload: Any, status: int = 200) -> None:
            data = json.dumps(payload, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                data = HTML.encode()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path == "/api/status":
                self.send_json(bot.status())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/api/update":
                    bot.update_once(False)
                    self.send_json({"ok": True})
                elif path == "/api/rebalance":
                    bot.update_once(True)
                    self.send_json({"ok": True})
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as exc:
                bot.log(f"request failed {path}: {exc}")
                bot.save()
                self.send_json({"ok": False, "error": str(exc)}, 500)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--universe-json", type=Path, default=UNIVERSE_JSON)
    parser.add_argument("--state-path", type=Path, default=STATE_PATH)
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--rebalance-days", type=int, default=7)
    parser.add_argument("--update-seconds", type=int, default=60)
    parser.add_argument("--fee", type=float, default=0.00035)
    parser.add_argument("--max-abs-weight", type=float, default=0.20)
    parser.add_argument("--gross-limit", type=float, default=1.0)
    parser.add_argument("--mean-shrink", type=float, default=0.50)
    parser.add_argument("--risk-aversion", type=float, default=1.0)
    parser.add_argument("--turnover-penalty", type=float, default=0.05)
    parser.add_argument("--min-trade-notional", type=float, default=5.0)
    parser.add_argument("--api-pause", type=float, default=0.15)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bot = PaperBot(args)
    server = LocalHTTPServer((args.host, args.port), make_handler(bot))
    print(f"paper dashboard: http://{args.host}:{args.port}", flush=True)
    thread = threading.Thread(target=bot.run_loop, daemon=True)
    thread.start()
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"use client";

import { useEffect, useRef, useState } from "react";

type Position = {
  qty: number;
  entry_price: number;
  price: number;
  weight: number;
  target_weight: number;
  unrealized_pnl: number;
};

type EquityPoint = {
  ts: string;
  equity: number;
};

type Status = {
  health: { ok: boolean; message: string };
  config: Record<string, string | number>;
  stats: {
    equity: number;
    total_return: number;
    drawdown: number;
    sharpe: number | null;
    gross_exposure: number;
    net_exposure: number;
    total_fees: number;
    total_funding: number;
  };
  positions: Record<string, Position>;
  equity_history: EquityPoint[];
  last_update: string | null;
  last_rebalance: string | null;
  next_rebalance_due: string | null;
  logs: string[];
};

const fmt = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });

function pct(x: number | null | undefined) {
  return Number.isFinite(x) ? `${((x as number) * 100).toFixed(2)}%` : "n/a";
}

function money(x: number | null | undefined) {
  return Number.isFinite(x) ? `$${fmt.format(x as number)}` : "n/a";
}

function cls(x: number | null | undefined) {
  return (x ?? 0) > 0 ? "pos" : (x ?? 0) < 0 ? "neg" : "";
}

function timeLabel(ts: string) {
  return new Date(ts).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function Metric({ label, value, klass = "" }: { label: string; value: string; klass?: string }) {
  return (
    <div className="metric">
      <div className="label">{label}</div>
      <div className={`value ${klass}`}>{value}</div>
    </div>
  );
}

function EquityChart({ points }: { points: EquityPoint[] }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;
    const leftPad = 46;
    const rightPad = 46;
    const topPad = 34;
    const bottomPad = 48;
    const plotW = w - leftPad - rightPad;
    const plotH = h - topPad - bottomPad;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "#d9dee7";
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i += 1) {
      const y = topPad + (i * plotH) / 4;
      ctx.beginPath();
      ctx.moveTo(leftPad, y);
      ctx.lineTo(w - rightPad, y);
      ctx.stroke();
    }
    if (!points.length) return;
    const vals = points.map((p) => p.equity);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const span = Math.max(max - min, 1e-9);
    ctx.strokeStyle = "#1d4ed8";
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = leftPad + (i * plotW) / Math.max(points.length - 1, 1);
      const y = topPad + plotH - ((p.equity - min) / span) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.strokeStyle = "#9aa3af";
    ctx.beginPath();
    ctx.moveTo(leftPad, topPad + plotH);
    ctx.lineTo(w - rightPad, topPad + plotH);
    ctx.stroke();
    ctx.fillStyle = "#17202a";
    ctx.font = "12px sans-serif";
    const pnl = vals[vals.length - 1] - vals[0];
    ctx.fillText(`Equity ${money(vals[vals.length - 1])}  PnL ${money(pnl)}`, leftPad, 18);
    ctx.fillStyle = "#647083";
    ctx.fillText(`${money(min)} - ${money(max)}`, leftPad, topPad + plotH + 16);
    const ticks = points.length === 1 ? [0] : [0, Math.floor((points.length - 1) / 2), points.length - 1];
    Array.from(new Set(ticks)).forEach((i, tickIndex, labels) => {
      const x = leftPad + (i * plotW) / Math.max(points.length - 1, 1);
      ctx.textAlign = tickIndex === 0 ? "left" : tickIndex === labels.length - 1 ? "right" : "center";
      ctx.fillText(timeLabel(points[i].ts), x, h - 8);
    });
    ctx.textAlign = "left";
  }, [points]);

  return <canvas ref={ref} />;
}

function WeightsChart({ rows }: { rows: Array<{ coin: string } & Position> }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;
    const pad = 32;
    ctx.clearRect(0, 0, w, h);
    const maxAbs = Math.max(0.2, ...rows.map((r) => Math.abs(r.weight)));
    const zero = h / 2;
    ctx.strokeStyle = "#17202a";
    ctx.beginPath();
    ctx.moveTo(pad, zero);
    ctx.lineTo(w - pad, zero);
    ctx.stroke();
    const bw = ((w - 2 * pad) / rows.length) * 0.72;
    rows.forEach((r, i) => {
      const x = pad + (i * (w - 2 * pad)) / rows.length + bw * 0.2;
      const y = zero - (r.weight / maxAbs) * (h / 2 - pad);
      ctx.fillStyle = r.weight >= 0 ? "#15803d" : "#b91c1c";
      ctx.fillRect(x, Math.min(y, zero), bw, Math.abs(y - zero));
      ctx.fillStyle = "#17202a";
      ctx.font = "11px sans-serif";
      ctx.save();
      ctx.translate(x + bw / 2, h - 8);
      ctx.rotate(-Math.PI / 5);
      ctx.fillText(r.coin, -10, 0);
      ctx.restore();
    });
    ctx.fillStyle = "#17202a";
    ctx.font = "12px sans-serif";
    ctx.fillText("Current weights", pad, 18);
  }, [rows]);

  return <canvas ref={ref} />;
}

export default function Page() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState("Loading");

  async function refresh() {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || response.statusText);
      setStatus(body);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 5000);
    return () => window.clearInterval(id);
  }, []);

  const rows = status ? Object.entries(status.positions).map(([coin, p]) => ({ coin, ...p })) : [];
  const stats = status?.stats;

  return (
    <>
      <header>
        <div>
          <h1>Signed Mean-Variance Paper Trading</h1>
          <div className="status">
            <span className={`dot ${status?.health.ok ? "ok" : "bad"}`} />
            <span>{status ? status.health.message : error}</span>
          </div>
        </div>
      </header>
      <main>
        <section className="metrics">
          <Metric label="Equity" value={money(stats?.equity)} klass={cls(stats?.total_return)} />
          <Metric label="Return" value={pct(stats?.total_return)} klass={cls(stats?.total_return)} />
          <Metric label="Drawdown" value={pct(stats?.drawdown)} klass={cls(-(stats?.drawdown ?? 0))} />
          <Metric label="Sharpe" value={stats?.sharpe == null ? "n/a" : fmt.format(stats.sharpe)} klass={cls(stats?.sharpe)} />
          <Metric label="Gross" value={pct(stats?.gross_exposure)} />
          <Metric label="Net" value={pct(stats?.net_exposure)} klass={cls(stats?.net_exposure)} />
          <Metric label="Fees" value={money(stats?.total_fees)} klass="neg" />
          <Metric label="Funding" value={money(stats?.total_funding)} klass={cls(stats?.total_funding)} />
        </section>
        <section className="grid">
          <div className="panel"><EquityChart points={status?.equity_history ?? []} /></div>
          <div className="panel"><WeightsChart rows={rows} /></div>
        </section>
        <section className="grid">
          <div className="panel">
            <table>
              <tbody>
                <tr><th>Coin</th><th>Qty</th><th>Weight</th><th>Target</th><th>Price</th><th>UPnL</th></tr>
                {rows.map((r) => (
                  <tr key={r.coin}>
                    <td>{r.coin}</td>
                    <td>{fmt.format(r.qty)}</td>
                    <td className={cls(r.weight)}>{pct(r.weight)}</td>
                    <td className={cls(r.target_weight)}>{pct(r.target_weight)}</td>
                    <td>{fmt.format(r.price)}</td>
                    <td className={cls(r.unrealized_pnl)}>{money(r.unrealized_pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel">
            <table>
              <tbody>
                <tr><th>Field</th><th>Value</th></tr>
                {Object.entries(status?.config ?? {}).map(([key, value]) => (
                  <tr key={key}><td>{key}</td><td>{String(value)}</td></tr>
                ))}
                <tr><td>last rebalance</td><td>{status?.last_rebalance ?? "never"}</td></tr>
                <tr><td>next rebalance</td><td>{status?.next_rebalance_due ?? "n/a"}</td></tr>
                <tr><td>last update</td><td>{status?.last_update ?? "never"}</td></tr>
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="log">{status?.logs?.join("\n") ?? error}</div>
        </section>
      </main>
    </>
  );
}

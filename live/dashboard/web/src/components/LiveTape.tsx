"use client";

import { useEffect, useMemo, useState } from "react";
import {
  supabase,
  type EquitySnapshot,
  type SyncState,
  type Trade,
} from "@/lib/supabase";
import { Sparkline } from "./Sparkline";

type Props = {
  initialTrades: Trade[];
  initialEquity: EquitySnapshot[];
  initialSync: SyncState | null;
};

export function LiveTape({ initialTrades, initialEquity, initialSync }: Props) {
  const [trades, setTrades] = useState(initialTrades);
  const [equity, setEquity] = useState(initialEquity);
  const [sync, setSync] = useState(initialSync);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const channel = supabase
      .channel("at_live")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "at_trades" },
        (payload) => {
          const next = payload.new as Trade;
          setTrades((prev) => {
            const idx = prev.findIndex((t) => t.trade_id === next.trade_id);
            if (idx === -1) return [next, ...prev].slice(0, 200);
            const copy = [...prev];
            copy[idx] = next;
            return copy;
          });
        },
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "at_equity_snapshots" },
        (payload) => {
          const next = payload.new as EquitySnapshot;
          setEquity((prev) => [...prev, next].slice(-500));
        },
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "at_sync_state" },
        (payload) => setSync(payload.new as SyncState),
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const latest = equity.at(-1);
  const open = useMemo(() => trades.filter((t) => t.is_open), [trades]);
  const closed = useMemo(
    () =>
      trades
        .filter((t) => !t.is_open)
        .sort((a, b) => (b.close_date ?? "").localeCompare(a.close_date ?? ""))
        .slice(0, 20),
    [trades],
  );

  const secsSinceSync = sync
    ? Math.max(0, Math.floor((now - new Date(sync.last_sync_at).getTime()) / 1000))
    : null;
  const isStale = secsSinceSync !== null && secsSinceSync > 120;

  return (
    <div className="max-w-6xl mx-auto px-6 sm:px-10 py-10 sm:py-16">
      <Header sync={sync} secsSinceSync={secsSinceSync} isStale={isStale} />
      <Summary latest={latest} />
      <section className="mt-10">
        <SectionHeading
          eyebrow="cumulative pnl"
          title="Equity curve"
          right={
            latest && (
              <span className="mono text-sm text-muted">
                {equity.length} snapshot{equity.length === 1 ? "" : "s"}
              </span>
            )
          }
        />
        <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <Sparkline points={equity.map((e) => ({ ts: e.ts, total_profit: e.total_profit }))} />
        </div>
      </section>

      <section className="mt-12 grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-2">
          <SectionHeading eyebrow="positions" title={`Open · ${open.length}`} />
          <OpenTable trades={open} />
        </div>
        <div className="lg:col-span-3">
          <SectionHeading eyebrow="history" title="Recent closes" />
          <ClosedTable trades={closed} />
        </div>
      </section>

      <Footer sync={sync} />
    </div>
  );
}

function Header({
  sync,
  secsSinceSync,
  isStale,
}: {
  sync: SyncState | null;
  secsSinceSync: number | null;
  isStale: boolean;
}) {
  return (
    <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-8 border-b border-[var(--color-border)]">
      <div>
        <p className="mono text-xs tracking-[0.2em] uppercase text-muted">
          algo-traders / live / track B
        </p>
        <h1 className="mt-2 text-3xl sm:text-4xl font-medium leading-tight">
          HmmSmaSlopeV2 — Hyperliquid paper tape
        </h1>
        <p className="mt-3 text-sm text-muted max-w-xl">
          A 30-day pre-registered Freqtrade dry-run. No real capital. The numbers below
          stream from the bot's own SQLite via a small sync sidecar.
        </p>
      </div>
      <div className="flex items-center gap-3 mono text-xs">
        <span
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 border ${
            isStale
              ? "border-[var(--color-loss)] text-[var(--color-loss)]"
              : "border-[var(--color-accent)] text-[var(--color-accent)]"
          }`}
        >
          <span
            className={`inline-block size-1.5 rounded-full ${
              isStale ? "bg-[var(--color-loss)]" : "bg-[var(--color-accent)] dot-live"
            }`}
          />
          {isStale ? "stale" : "live"}
        </span>
        <span className="text-muted">
          {sync
            ? `synced ${secsSinceSync}s ago`
            : "no sync yet"}
        </span>
      </div>
    </header>
  );
}

function Summary({ latest }: { latest: EquitySnapshot | undefined }) {
  if (!latest) {
    return (
      <div className="mt-8 text-muted mono text-sm">
        Waiting for the first sync from the VPS…
      </div>
    );
  }
  const pnl = latest.total_profit;
  const pct = latest.total_profit_pct;
  const sign = pnl >= 0 ? "+" : "";
  const color = pnl >= 0 ? "text-[var(--color-accent)]" : "text-[var(--color-loss)]";

  return (
    <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-6">
      <Metric label="Balance" value={`$${latest.balance.toFixed(2)}`} />
      <Metric
        label="Total PnL"
        value={
          <span className={`${color}`}>
            {sign}
            {pnl.toFixed(2)}{" "}
            <span className="text-base text-muted">({sign}
            {pct.toFixed(2)}%)</span>
          </span>
        }
      />
      <Metric label="Closed trades" value={String(latest.closed_trades)} />
      <Metric
        label="Best / worst pair"
        value={
          <span className="mono text-base">
            {latest.best_pair ?? "—"}
            <span className="text-muted mx-2">·</span>
            {latest.worst_pair ?? "—"}
          </span>
        }
      />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="mono text-[10px] tracking-[0.18em] uppercase text-muted">{label}</p>
      <p className="mt-2 mono text-2xl font-medium leading-none">{value}</p>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  right,
}: {
  eyebrow: string;
  title: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <p className="mono text-[10px] tracking-[0.2em] uppercase text-muted">{eyebrow}</p>
        <h2 className="mt-1 text-lg font-medium">{title}</h2>
      </div>
      {right}
    </div>
  );
}

function OpenTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return (
      <div className="mt-4 rounded-md border border-dashed border-[var(--color-border)] p-6 text-sm text-muted mono">
        No open positions.
      </div>
    );
  }
  return (
    <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <table className="w-full mono text-sm">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-[0.18em] text-muted">
            <th className="px-4 py-3">Pair</th>
            <th className="px-4 py-3 text-right">Entry</th>
            <th className="px-4 py-3 text-right">Stake</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.trade_id} className="border-t border-[var(--color-border)]">
              <td className="px-4 py-2.5">{t.pair}</td>
              <td className="px-4 py-2.5 text-right">{t.open_rate.toFixed(4)}</td>
              <td className="px-4 py-2.5 text-right">{t.stake_amount.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClosedTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return (
      <div className="mt-4 rounded-md border border-dashed border-[var(--color-border)] p-6 text-sm text-muted mono">
        No closed trades yet.
      </div>
    );
  }
  return (
    <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <table className="w-full mono text-sm">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-[0.18em] text-muted">
            <th className="px-4 py-3">When</th>
            <th className="px-4 py-3">Pair</th>
            <th className="px-4 py-3">Exit</th>
            <th className="px-4 py-3 text-right">PnL</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const pnl = t.close_profit_abs ?? 0;
            const pct = (t.close_profit ?? 0) * 100;
            const color = pnl >= 0 ? "text-[var(--color-accent)]" : "text-[var(--color-loss)]";
            const when = t.close_date
              ? new Date(t.close_date).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "—";
            return (
              <tr key={t.trade_id} className="border-t border-[var(--color-border)]">
                <td className="px-4 py-2.5 text-muted">{when}</td>
                <td className="px-4 py-2.5">{t.pair}</td>
                <td className="px-4 py-2.5 text-muted">{t.exit_reason ?? "—"}</td>
                <td className={`px-4 py-2.5 text-right ${color}`}>
                  {pnl >= 0 ? "+" : ""}
                  {pnl.toFixed(2)}{" "}
                  <span className="text-muted">({pct >= 0 ? "+" : ""}{pct.toFixed(2)}%)</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Footer({ sync }: { sync: SyncState | null }) {
  return (
    <footer className="mt-16 pt-8 border-t border-[var(--color-border)] mono text-xs text-muted flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <span>
        Read-only view. The bot pre-registers its kill criteria; see{" "}
        <a
          href="https://github.com/davidcagoh/algo-traders"
          className="underline decoration-dotted hover:text-[var(--color-text)]"
        >
          the repo
        </a>{" "}
        for methodology.
      </span>
      <span>sync_version: {sync?.sync_version ?? "—"}</span>
    </footer>
  );
}

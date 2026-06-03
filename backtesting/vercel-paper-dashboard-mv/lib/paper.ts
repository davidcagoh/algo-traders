import { Redis } from "@upstash/redis";

export const STATUS_KEY = "signed_mv_paper_state";

const API_URL = "https://api.hyperliquid.xyz/info";
const INTERVAL_MS = 3_600_000;
const MAX_CANDLES = 5000;
const UNIVERSE = ["BTC", "HYPE", "PAXG", "TRX", "WLFI", "VVV", "TON", "ZRO", "XPL"];

const CONFIG = {
  strategy: "signed_mean_variance",
  initial_equity: 10_000,
  lookback_days: 60,
  rebalance_days: 7,
  update_seconds: 3600,
  fee: 0.00035,
  max_abs_weight: 0.2,
  gross_limit: 1.0,
  mean_shrink: 0.5,
  risk_aversion: 1.0,
  turnover_penalty: 0.05,
  min_trade_notional: 5
};

type Position = {
  qty: number;
  entry_price: number;
  realized_pnl: number;
};

type Trade = {
  ts: string;
  coin: string;
  delta_qty: number;
  price: number;
  notional: number;
  fee: number;
  reason: string;
};

type FundingEvent = {
  ts: number;
  coin: string;
  rate: number;
  qty: number;
  pnl: number;
};

type EquityPoint = {
  ts: string;
  equity: number;
  cash: number;
  gross: number;
  net: number;
  drawdown: number;
};

export type PaperState = {
  version: number;
  started_at: string;
  last_update: string | null;
  last_rebalance: string | null;
  cash: number;
  initial_equity: number;
  positions: Record<string, Position>;
  last_prices: Record<string, number>;
  last_funding_time_ms: Record<string, number>;
  target_weights: Record<string, number>;
  equity_history: EquityPoint[];
  trades: Trade[];
  funding_events: FundingEvent[];
  logs: string[];
};

type StatusPosition = Position & {
  price: number;
  weight: number;
  target_weight: number;
  unrealized_pnl: number;
};

export type PaperStatus = {
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
  positions: Record<string, StatusPosition>;
  equity_history: EquityPoint[];
  last_update: string | null;
  last_rebalance: string | null;
  next_rebalance_due: string | null;
  logs: string[];
};

type Candle = { t: number; c: string };
type FundingRecord = { time: number; fundingRate: string };

export function redisFromEnv(): Redis | null {
  const hasKv = process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN;
  const hasUpstash = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!hasKv && !hasUpstash) return null;
  return Redis.fromEnv();
}

export async function loadState(redis: Redis): Promise<PaperState | null> {
  return await redis.get<PaperState>(STATUS_KEY);
}

export async function saveState(redis: Redis, state: PaperState) {
  await redis.set(STATUS_KEY, state);
}

export function initialState(): PaperState {
  const now = new Date().toISOString();
  const nowMs = Date.now();
  return {
    version: 1,
    started_at: now,
    last_update: null,
    last_rebalance: null,
    cash: CONFIG.initial_equity,
    initial_equity: CONFIG.initial_equity,
    positions: Object.fromEntries(UNIVERSE.map((coin) => [coin, { qty: 0, entry_price: 0, realized_pnl: 0 }])),
    last_prices: {},
    last_funding_time_ms: Object.fromEntries(UNIVERSE.map((coin) => [coin, nowMs])),
    target_weights: Object.fromEntries(UNIVERSE.map((coin) => [coin, 0])),
    equity_history: [],
    trades: [],
    funding_events: [],
    logs: []
  };
}

function log(state: PaperState, message: string) {
  state.logs.push(`${new Date().toISOString()} ${message}`);
  state.logs = state.logs.slice(-200);
}

async function postInfo<T>(payload: Record<string, unknown>, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: "no-store"
    });
    if (!response.ok) throw new Error(`Hyperliquid ${response.status}`);
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchMids(): Promise<Record<string, number>> {
  const data = await postInfo<Record<string, string>>({ type: "allMids" }, 10_000);
  return Object.fromEntries(UNIVERSE.filter((coin) => data[coin] != null).map((coin) => [coin, Number(data[coin])]));
}

async function fetchCandles(coin: string): Promise<Array<{ date: Date; close: number }>> {
  const endTime = Date.now();
  const startTime = endTime - INTERVAL_MS * MAX_CANDLES;
  const data = await postInfo<Candle[]>(
    {
      type: "candleSnapshot",
      req: { coin, interval: "1h", startTime, endTime }
    },
    30_000
  );
  if (!Array.isArray(data) || data.length === 0) throw new Error(`No candle data for ${coin}`);
  return data.map((row) => ({ date: new Date(row.t), close: Number(row.c) })).sort((a, b) => a.date.getTime() - b.date.getTime());
}

async function fetchFundingSince(coin: string, startTime: number): Promise<FundingRecord[]> {
  const endTime = Date.now();
  if (startTime >= endTime - 60_000) return [];
  const data = await postInfo<FundingRecord[]>(
    { type: "fundingHistory", coin, startTime: startTime + 1, endTime },
    20_000
  );
  return Array.isArray(data) ? data : [];
}

async function fetchFundingWindow(coin: string, startTime: number, endTime: number): Promise<FundingRecord[]> {
  const data = await postInfo<FundingRecord[]>(
    { type: "fundingHistory", coin, startTime, endTime },
    20_000
  );
  return Array.isArray(data) ? data : [];
}

function dayKey(date: Date) {
  return date.toISOString().slice(0, 10);
}

function dailyCloses(candles: Array<{ date: Date; close: number }>): Map<string, number> {
  const out = new Map<string, number>();
  for (const candle of candles) out.set(dayKey(candle.date), candle.close);
  return out;
}

function pctChange(values: number[]) {
  const out: number[] = [];
  for (let i = 1; i < values.length; i += 1) out.push(values[i] / values[i - 1] - 1);
  return out;
}

async function signedReturnHistory(): Promise<{ dates: string[]; returns: number[][] }> {
  const candleMaps = new Map<string, Map<string, number>>();
  for (const coin of UNIVERSE) {
    candleMaps.set(coin, dailyCloses(await fetchCandles(coin)));
  }

  const commonDates = [...candleMaps.values()].reduce<string[] | null>((acc, map) => {
    const dates = [...map.keys()];
    return acc == null ? dates : acc.filter((date) => map.has(date));
  }, null) ?? [];
  commonDates.sort();
  const dates = commonDates.slice(-(CONFIG.lookback_days + 1));
  if (dates.length < CONFIG.lookback_days + 1) {
    throw new Error(`Only ${dates.length - 1} daily observations, need ${CONFIG.lookback_days}`);
  }

  const priceReturnsByCoin = UNIVERSE.map((coin) => {
    const closes = dates.map((date) => candleMaps.get(coin)?.get(date) ?? NaN);
    return pctChange(closes);
  });

  const startMs = new Date(`${dates[0]}T00:00:00Z`).getTime();
  const endMs = Date.now();
  const fundingByCoin: number[][] = [];
  for (const coin of UNIVERSE) {
    const daily = new Map<string, number>();
    for (const record of await fetchFundingWindow(coin, startMs, endMs)) {
      const date = dayKey(new Date(record.time));
      daily.set(date, (daily.get(date) ?? 0) + Number(record.fundingRate));
    }
    fundingByCoin.push(dates.slice(1).map((date) => daily.get(date) ?? 0));
  }

  const returns = dates.slice(1).map((_, row) =>
    UNIVERSE.map((_, col) => priceReturnsByCoin[col][row] - fundingByCoin[col][row])
  );
  return { dates: dates.slice(1), returns };
}

function means(rows: number[][]) {
  const n = rows.length;
  return UNIVERSE.map((_, col) => rows.reduce((sum, row) => sum + row[col], 0) / n);
}

function shrunkCov(rows: number[][]) {
  const n = rows.length;
  const mu = means(rows);
  const cov = UNIVERSE.map(() => UNIVERSE.map(() => 0));
  for (const row of rows) {
    for (let i = 0; i < UNIVERSE.length; i += 1) {
      for (let j = 0; j < UNIVERSE.length; j += 1) {
        cov[i][j] += (row[i] - mu[i]) * (row[j] - mu[j]);
      }
    }
  }
  for (let i = 0; i < UNIVERSE.length; i += 1) {
    for (let j = 0; j < UNIVERSE.length; j += 1) cov[i][j] /= Math.max(n - 1, 1);
  }
  const avgVar = cov.reduce((sum, row, i) => sum + row[i], 0) / UNIVERSE.length;
  const shrink = 0.1;
  for (let i = 0; i < UNIVERSE.length; i += 1) {
    for (let j = 0; j < UNIVERSE.length; j += 1) {
      cov[i][j] = (1 - shrink) * cov[i][j] + (i === j ? shrink * avgVar : 0);
    }
  }
  return cov;
}

function gross(weights: number[]) {
  return weights.reduce((sum, value) => sum + Math.abs(value), 0);
}

function project(weights: number[]) {
  const out = weights.map((w) => Math.max(-CONFIG.max_abs_weight, Math.min(CONFIG.max_abs_weight, w)));
  const g = gross(out);
  if (g > CONFIG.gross_limit) {
    for (let i = 0; i < out.length; i += 1) out[i] = (out[i] / g) * CONFIG.gross_limit;
  }
  return out;
}

function objective(weights: number[], mu: number[], cov: number[][], previous: number[]) {
  const ret = weights.reduce((sum, weight, i) => sum + mu[i] * weight, 0);
  let risk = 0;
  for (let i = 0; i < weights.length; i += 1) {
    for (let j = 0; j < weights.length; j += 1) risk += weights[i] * cov[i][j] * weights[j];
  }
  const churn = weights.reduce((sum, weight, i) => sum + (weight - previous[i]) ** 2, 0);
  return ret - CONFIG.risk_aversion * risk - CONFIG.turnover_penalty * churn;
}

function signalSeed(mu: number[]) {
  const weights = Array(UNIVERSE.length).fill(0);
  let used = 0;
  for (const idx of mu.map((value, i) => ({ value, i })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).map((x) => x.i)) {
    if (Math.abs(mu[idx]) <= 1e-12 || used >= CONFIG.gross_limit - 1e-12) break;
    const size = Math.min(CONFIG.max_abs_weight, CONFIG.gross_limit - used);
    weights[idx] = Math.sign(mu[idx]) * size;
    used += size;
  }
  return weights;
}

function solveWeights(rows: number[][], previous: number[]) {
  const mu = means(rows).map((value) => value * 365 * CONFIG.mean_shrink);
  const cov = shrunkCov(rows);
  let best = project(previous);
  let bestScore = objective(best, mu, cov, previous);

  for (const seed of [project(previous), signalSeed(mu)]) {
    let weights = seed.slice();
    let step = 0.1;
    for (let iter = 0; iter < 500; iter += 1) {
      const grad = weights.map((weight, i) => {
        const riskGrad = 2 * weights.reduce((sum, wj, j) => sum + cov[i][j] * wj, 0);
        return mu[i] - CONFIG.risk_aversion * riskGrad - 2 * CONFIG.turnover_penalty * (weight - previous[i]);
      });
      const candidate = project(weights.map((weight, i) => weight + step * grad[i]));
      const candidateScore = objective(candidate, mu, cov, previous);
      if (candidateScore >= objective(weights, mu, cov, previous)) {
        weights = candidate;
      } else {
        step *= 0.5;
      }
      if (step < 1e-5) break;
    }
    const score = objective(weights, mu, cov, previous);
    if (score > bestScore) {
      best = weights;
      bestScore = score;
    }
  }
  return best.map((w) => (Math.abs(w) < 1e-10 ? 0 : w));
}

function markEquity(state: PaperState, prices: Record<string, number>) {
  let equity = state.cash;
  for (const coin of UNIVERSE) {
    const position = state.positions[coin];
    const price = prices[coin];
    if (!position || price == null) continue;
    equity += position.qty * (price - position.entry_price);
  }
  return equity;
}

function currentWeights(state: PaperState, prices: Record<string, number>, equity: number) {
  if (equity <= 0) return Array(UNIVERSE.length).fill(0);
  return UNIVERSE.map((coin) => state.positions[coin].qty * (prices[coin] ?? 0) / equity);
}

function updatePositionForTrade(position: Position, delta: number, price: number) {
  const oldQty = position.qty;
  const oldEntry = position.entry_price;
  if (Math.abs(oldQty) <= 1e-12) {
    position.qty = delta;
    position.entry_price = Math.abs(delta) > 1e-12 ? price : 0;
    return;
  }
  if (oldQty * delta >= 0) {
    const newQty = oldQty + delta;
    position.entry_price = Math.abs(newQty) > 1e-12
      ? (Math.abs(oldQty) * oldEntry + Math.abs(delta) * price) / Math.abs(newQty)
      : 0;
    position.qty = newQty;
    return;
  }
  const closeQty = Math.min(Math.abs(delta), Math.abs(oldQty));
  const realized = closeQty * Math.sign(oldQty) * (price - oldEntry);
  position.realized_pnl += realized;
  const newQty = oldQty + delta;
  position.qty = newQty;
  position.entry_price = oldQty * newQty < 0 ? price : Math.abs(newQty) > 1e-12 ? oldEntry : 0;
}

async function applyFunding(state: PaperState, prices: Record<string, number>) {
  for (const coin of UNIVERSE) {
    const lastMs = state.last_funding_time_ms[coin] ?? Date.now();
    const records = await fetchFundingSince(coin, lastMs);
    const qty = state.positions[coin].qty;
    for (const record of records) {
      const ts = Number(record.time);
      const rate = Number(record.fundingRate);
      const pnl = -qty * (prices[coin] ?? 0) * rate;
      state.cash += pnl;
      state.funding_events.push({ ts, coin, rate, qty, pnl });
      state.last_funding_time_ms[coin] = Math.max(ts, state.last_funding_time_ms[coin] ?? 0);
    }
    if (records.length) log(state, `applied ${records.length} funding records for ${coin}`);
  }
  state.funding_events = state.funding_events.slice(-500);
}

async function rebalance(state: PaperState, prices: Record<string, number>, reason: string) {
  const { returns } = await signedReturnHistory();
  const equity = markEquity(state, prices);
  const previous = currentWeights(state, prices, equity);
  const weights = solveWeights(returns.slice(-CONFIG.lookback_days), previous);
  const targets = Object.fromEntries(UNIVERSE.map((coin, i) => [coin, weights[i]]));
  state.target_weights = targets;

  let totalFee = 0;
  for (const coin of UNIVERSE) {
    const price = prices[coin];
    const desiredQty = (targets[coin] * equity) / price;
    const position = state.positions[coin];
    const delta = desiredQty - position.qty;
    if (Math.abs(delta * price) < CONFIG.min_trade_notional) continue;
    const fee = Math.abs(delta * price) * CONFIG.fee;
    state.cash -= fee;
    totalFee += fee;
    updatePositionForTrade(position, delta, price);
    state.trades.push({
      ts: new Date().toISOString(),
      coin,
      delta_qty: delta,
      price,
      notional: delta * price,
      fee,
      reason
    });
  }
  state.trades = state.trades.slice(-500);
  state.last_rebalance = new Date().toISOString();
  if (totalFee) log(state, `rebalance ${reason}: fees=${totalFee.toFixed(4)}`);
}

function rebalanceDue(state: PaperState) {
  if (!state.last_rebalance) return true;
  return new Date(state.last_rebalance).getTime() + CONFIG.rebalance_days * 86_400_000 <= Date.now();
}

export async function tick(state: PaperState | null, forceRebalance = false): Promise<PaperState> {
  const next = state ?? initialState();
  const prices = await fetchMids();
  const missing = UNIVERSE.filter((coin) => prices[coin] == null);
  if (missing.length) throw new Error(`Missing prices: ${missing.join(", ")}`);
  next.last_prices = prices;
  await applyFunding(next, prices);
  if (forceRebalance || rebalanceDue(next)) await rebalance(next, prices, forceRebalance ? "manual" : "scheduled");

  const equity = markEquity(next, prices);
  const weights = currentWeights(next, prices, equity);
  const peak = Math.max(equity, ...next.equity_history.map((row) => row.equity));
  next.equity_history.push({
    ts: new Date().toISOString(),
    equity,
    cash: next.cash,
    gross: gross(weights),
    net: weights.reduce((sum, weight) => sum + weight, 0),
    drawdown: peak ? equity / peak - 1 : 0
  });
  next.equity_history = next.equity_history.slice(-5000);
  next.last_update = new Date().toISOString();
  return next;
}

export function statusFromState(state: PaperState): PaperStatus {
  const prices = state.last_prices;
  const equity = Object.keys(prices).length ? markEquity(state, prices) : state.cash;
  const weights = Object.keys(prices).length ? currentWeights(state, prices, equity) : Array(UNIVERSE.length).fill(0);
  const peak = Math.max(equity, ...state.equity_history.map((row) => row.equity));
  const returns = state.equity_history.slice(1).map((row, i) => row.equity / state.equity_history[i].equity - 1);
  const mean = returns.reduce((sum, value) => sum + value, 0) / Math.max(returns.length, 1);
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(returns.length - 1, 1);
  const std = Math.sqrt(variance);
  const sharpe = returns.length >= 30 && std > 0 ? (mean / std) * Math.sqrt(365 * 24) : null;
  const stale = !state.last_update || new Date(state.last_update).getTime() < Date.now() - CONFIG.update_seconds * 3000;
  const lastRebalance = state.last_rebalance;

  return {
    health: { ok: !stale, message: stale ? "stale or starting" : "ok" },
    config: {
      strategy: CONFIG.strategy,
      lookback_days: CONFIG.lookback_days,
      rebalance_days: CONFIG.rebalance_days,
      mean_shrink: CONFIG.mean_shrink,
      risk_aversion: CONFIG.risk_aversion,
      max_abs_weight: CONFIG.max_abs_weight,
      gross_limit: CONFIG.gross_limit
    },
    stats: {
      equity,
      total_return: equity / state.initial_equity - 1,
      drawdown: peak ? equity / peak - 1 : 0,
      sharpe,
      gross_exposure: gross(weights),
      net_exposure: weights.reduce((sum, weight) => sum + weight, 0),
      total_fees: state.trades.reduce((sum, trade) => sum + Math.abs(trade.fee), 0),
      total_funding: state.funding_events.reduce((sum, event) => sum + event.pnl, 0)
    },
    positions: Object.fromEntries(UNIVERSE.map((coin, i) => {
      const position = state.positions[coin];
      const price = prices[coin] ?? 0;
      return [coin, {
        ...position,
        price,
        weight: weights[i] ?? 0,
        target_weight: state.target_weights[coin] ?? 0,
        unrealized_pnl: price ? position.qty * (price - position.entry_price) : 0
      }];
    })),
    equity_history: state.equity_history.slice(-1000),
    last_update: state.last_update,
    last_rebalance: lastRebalance,
    next_rebalance_due: lastRebalance ? new Date(new Date(lastRebalance).getTime() + CONFIG.rebalance_days * 86_400_000).toISOString() : null,
    logs: state.logs.slice(-80)
  };
}

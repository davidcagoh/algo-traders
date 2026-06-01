import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !key) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
      "Copy .env.example to .env.local and fill them in.",
  );
}

export const supabase = createClient(url, key, {
  auth: { persistSession: false },
  realtime: { params: { eventsPerSecond: 5 } },
});

export type Trade = {
  trade_id: number;
  pair: string;
  is_open: boolean;
  open_date: string;
  close_date: string | null;
  open_rate: number;
  close_rate: number | null;
  amount: number;
  stake_amount: number;
  close_profit: number | null;
  close_profit_abs: number | null;
  exit_reason: string | null;
  strategy: string | null;
  fetched_at: string;
};

export type EquitySnapshot = {
  id: number;
  ts: string;
  balance: number;
  open_trades: number;
  closed_trades: number;
  total_profit: number;
  total_profit_pct: number;
  best_pair: string | null;
  worst_pair: string | null;
};

export type SyncState = {
  id: number;
  last_sync_at: string;
  sync_version: string | null;
  notes: string | null;
};

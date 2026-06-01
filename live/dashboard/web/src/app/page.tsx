import { LiveTape } from "@/components/LiveTape";
import { supabase, type EquitySnapshot, type SyncState, type Trade } from "@/lib/supabase";

// Always fresh on server render; client realtime takes it from there.
export const revalidate = 0;

export default async function Page() {
  const [trades, equity, sync] = await Promise.all([
    supabase
      .from("at_trades")
      .select("*")
      .order("open_date", { ascending: false })
      .limit(200),
    supabase
      .from("at_equity_snapshots")
      .select("*")
      .order("ts", { ascending: true })
      .limit(500),
    supabase.from("at_sync_state").select("*").eq("id", 1).maybeSingle(),
  ]);

  return (
    <LiveTape
      initialTrades={(trades.data as Trade[] | null) ?? []}
      initialEquity={(equity.data as EquitySnapshot[] | null) ?? []}
      initialSync={(sync.data as SyncState | null) ?? null}
    />
  );
}

import { NextResponse } from "next/server";
import { loadState, redisFromEnv, statusFromState } from "../../../lib/paper";

export const runtime = "nodejs";

export async function GET() {
  const redis = redisFromEnv();
  if (!redis) {
    return NextResponse.json(
      { ok: false, error: "KV_REST_API_URL/KV_REST_API_TOKEN required." },
      { status: 503 }
    );
  }

  const state = await loadState(redis);
  if (!state) {
    return NextResponse.json({ ok: false, error: "No paper state yet. Wait for cron or call /api/tick once." }, { status: 404 });
  }

  return NextResponse.json(statusFromState(state));
}

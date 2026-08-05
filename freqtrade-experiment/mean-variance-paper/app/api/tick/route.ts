import { NextRequest, NextResponse } from "next/server";
import { loadState, redisFromEnv, saveState, statusFromState, tick } from "../../../lib/paper";

export const runtime = "nodejs";
export const maxDuration = 60;

function authorized(request: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return true;
  const supplied = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  return supplied === secret;
}

async function runTick(request: NextRequest) {
  if (!authorized(request)) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  const redis = redisFromEnv();
  if (!redis) {
    return NextResponse.json(
      { ok: false, error: "KV_REST_API_URL/KV_REST_API_TOKEN required." },
      { status: 503 }
    );
  }
  const force = request.nextUrl.searchParams.get("force") === "1";
  const state = await tick(await loadState(redis), force);
  await saveState(redis, state);
  return NextResponse.json({ ok: true, status: statusFromState(state) });
}

export async function GET(request: NextRequest) {
  return runTick(request);
}

export async function POST(request: NextRequest) {
  return runTick(request);
}

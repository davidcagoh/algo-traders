#!/bin/sh
# Track B liveness probe.
# Hits Freqtrade's REST /ping; only pings healthchecks.io if it answers 200.
# Silence on the upstream side = silence to healthchecks.io = alert fires.

set -eu

api_url="http://freqtrade:8080/api/v1/ping"
status=$(curl -fsS -u "${FT_API_USERNAME}:${FT_API_PASSWORD}" -m 10 "${api_url}" 2>/dev/null || echo "")

case "${status}" in
  *pong*)
    curl -fsS -m 10 "${HEALTHCHECK_URL}" >/dev/null || true
    ;;
  *)
    # Send /fail to healthchecks.io so the dashboard reflects the cause, not
    # just "stopped pinging". /fail is supported on all check URLs.
    curl -fsS -m 10 "${HEALTHCHECK_URL}/fail" >/dev/null || true
    ;;
esac

#!/usr/bin/env bash
# Session Start Routine baseline eval.
# Runs LongOnlyStrategy on 1h BTC/USDC:USDC, ~200 days.
# See wiki/decisions/003-baseline-eval.md to change the baseline.
#
# Primary metric: Calmar (CAGR / |MDD|). Sharpe always shown as sanity check.
# Freqtrade's backtest summary prints both; scan the "BACKTESTING REPORT" block.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FT="./freqtrade/.venv/bin/freqtrade"
if [[ ! -x "$FT" ]]; then
  echo "freqtrade not found at $FT — see wiki/_index.md Setup section." >&2
  exit 1
fi

"$FT" backtesting \
  --userdir user_data \
  -c user_data/config.json \
  --data-format-ohlcv feather \
  -s LongOnlyStrategy -i 1h \
  -p BTC/USDC:USDC \
  --eps --max-open-trades 1

# Regenerate Pareto chart (non-fatal — requires: pip install matplotlib).
# The old bar-chart leaderboard generator is deprecated (see README); the
# Pareto chart replaced it after strategies became regime-conditional.
PYTHON="$(dirname "$FT")/python"
if [[ -x "$PYTHON" ]]; then
  "$PYTHON" "$(dirname "${BASH_SOURCE[0]}")/generate_pareto_chart.py" \
    || echo "Warning: chart generation failed — run: pip install matplotlib in the freqtrade venv" >&2
fi

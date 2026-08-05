#!/usr/bin/env bash
# Install the sync sidecar on the VPS. Run as root from this directory.
# Idempotent.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f /etc/algo-traders-sync.env ]]; then
  echo "==> /etc/algo-traders-sync.env not found."
  echo "    Copy algo-traders-sync.env.example to /etc/algo-traders-sync.env,"
  echo "    fill in SUPABASE_SERVICE_KEY and FREQTRADE_DB_PATH, chmod 600, then re-run."
  exit 1
fi
chmod 600 /etc/algo-traders-sync.env

install -d /opt/algo-traders
install -m 0755 "${SRC}/sync.py" /opt/algo-traders/sync.py

install -m 0644 "${SRC}/algo-traders-sync.service" /etc/systemd/system/algo-traders-sync.service
install -m 0644 "${SRC}/algo-traders-sync.timer"   /etc/systemd/system/algo-traders-sync.timer

systemctl daemon-reload
systemctl enable --now algo-traders-sync.timer

echo "==> Installed."
echo "    Tail logs: journalctl -u algo-traders-sync.service -f"
echo "    Force run: systemctl start algo-traders-sync.service"

#!/bin/bash
# AI No Key — double-click to open (Mac)
cd "$(dirname "$0")"

# Prefer project venv
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  PY="python3"
fi

# Load UniFi secrets if present
if [ -f ".unifi.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".unifi.env"
  set +a
fi

PORT=8787
URL="http://127.0.0.1:${PORT}"

# Open browser after short delay so server can bind
(sleep 1.2 && open "$URL") &

echo "AI No Key"
echo "  $URL"
echo "  Ctrl+C to stop"
echo ""

exec "$PY" scripts/serve_ui.py --host 127.0.0.1 --port "$PORT"

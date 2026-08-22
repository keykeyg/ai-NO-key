#!/bin/bash
# AI No Key — daily double-click launcher (Mac)
cd "$(dirname "$0")"

# Prefer project venv
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  echo "Not installed yet."
  echo "Double-click  Install AI No Key.command  first (one time)."
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

# Load UniFi secrets if present
if [ -f ".unifi.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".unifi.env"
  set +a
fi

# Quick OSNet status (non-fatal)
if "$PY" -c "from torchreid.utils import FeatureExtractor" 2>/dev/null; then
  REID="OSNet ready"
else
  REID="OSNet missing — using weaker fallback (re-run Install)"
fi

PORT=8787
URL="http://127.0.0.1:${PORT}"

(sleep 1.2 && open "$URL") &

echo "AI No Key"
echo "  $URL"
echo "  $REID"
echo "  Ctrl+C to stop"
echo ""

exec "$PY" scripts/serve_ui.py --host 127.0.0.1 --port "$PORT"

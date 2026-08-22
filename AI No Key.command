#!/bin/bash
# Night Trail — daily double-click launcher (Mac)
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  echo "Not installed yet."
  echo "Double-click  Install AI No Key.command  first (one time)."
  echo "Or open BROTHER_SETUP.md"
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

if [ -f ".unifi.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".unifi.env"
  set +a
fi

if "$PY" -c "from torchreid.utils import FeatureExtractor" 2>/dev/null; then
  REID="OSNet ready"
else
  REID="OSNet missing — using weaker fallback (re-run Install)"
fi

PORT=8787
URL="http://127.0.0.1:${PORT}"

(sleep 1.2 && open "$URL") &

echo "Night Trail"
echo "  $URL"
echo "  $REID"
echo "  Ctrl+C to stop"
echo ""

exec "$PY" scripts/serve_ui.py --host 127.0.0.1 --port "$PORT"

#!/bin/bash
# AI No Key — script wrapped by Platypus into AI No Key.app
# Finds project root (folder that contains the .app), then starts the UI.

set -e

# When run from Platypus .app:
#   this script lives at:  Something.app/Contents/Resources/script
# Project root is the folder that contains the .app
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)"
if [[ "$SCRIPT_PATH" == *".app/Contents/Resources"* ]]; then
  ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"
else
  # Fallback: running from repo scripts/
  ROOT="$(cd "$SCRIPT_PATH/.." && pwd)"
fi

cd "$ROOT"

# Prefer project venv
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
  PY="$ROOT/venv/bin/python"
else
  osascript -e 'display dialog "AI No Key is not installed yet.

Double-click Install AI No Key.command first (one time)." buttons {"OK"} default button 1 with icon caution'
  exit 1
fi

# Load UniFi secrets if present
if [ -f "$ROOT/.unifi.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.unifi.env"
  set +a
fi

PORT=8787
URL="http://127.0.0.1:${PORT}"

# Open browser after server can bind
(sleep 1.5 && open "$URL") &

exec "$PY" "$ROOT/scripts/serve_ui.py" --host 127.0.0.1 --port "$PORT"

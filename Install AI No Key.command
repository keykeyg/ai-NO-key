#!/bin/bash
# AI No Key — first-run installer for Mac (you + brother)
# Double-click once. Sets up venv, deps, OSNet, and the daily launcher.
cd "$(dirname "$0")"
set -e

clear 2>/dev/null || true
echo "========================================"
echo "  AI No Key — Mac Installer"
echo "  Strongest person ReID (OSNet)"
echo "========================================"
echo ""

# Need Python 3.10+
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install from python.org or:"
  echo "  brew install python@3.11"
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYVER"
echo ""

# Create venv
if [ ! -x ".venv/bin/python" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
else
  echo "[1/4] Virtual environment already exists"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo ""
echo "[2/4] Installing core packages (this can take a few minutes)..."
python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt

echo ""
echo "[3/4] Installing OSNet (strongest body model for dark bars / black shirts)..."
bash scripts/setup_reid.sh || true

echo ""
echo "[4/4] Making launchers double-clickable..."
chmod +x "AI No Key.command" 2>/dev/null || true
chmod +x "Install AI No Key.command" 2>/dev/null || true
chmod +x scripts/setup_reid.sh 2>/dev/null || true

# Seed config from example if missing
if [ ! -f config.yaml ] && [ -f config.example.yaml ]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml from example (edit host / cameras as needed)"
fi

echo ""
echo "========================================"
echo "  Install complete"
echo "========================================"
echo ""
echo "Next:"
echo "  1. Double-click  AI No Key.command"
echo "  2. First-run wizard → UniFi host / user / password"
echo "  3. Tag a person → Search 20:00 to 03:00"
echo ""
echo "OSNet is the body model. NVR pull is the default source."
echo ""
read -r -p "Press Return to close..."

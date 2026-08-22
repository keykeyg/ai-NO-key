#!/bin/bash
# Night Trail — first-run installer for Mac (Apple Silicon preferred)
cd "$(dirname "$0")"
set -e

clear 2>/dev/null || true
echo "========================================"
echo "  Night Trail — Mac Installer"
echo "  Strongest person ReID (OSNet)"
echo "========================================"
echo ""

# Prefer Apple Silicon Homebrew Python 3.11 (avoid Intel /usr/local python)
PY=""
for candidate in \
  /opt/homebrew/bin/python3.11 \
  /opt/homebrew/bin/python3.12 \
  /opt/homebrew/bin/python3 \
  /usr/bin/python3
do
  if [ -x "$candidate" ]; then
    # Skip x86_64 binaries on Apple Silicon when possible
    arch=$("$candidate" -c 'import platform; print(platform.machine())' 2>/dev/null || echo unknown)
    if [ "$arch" = "arm64" ] || [ "$candidate" = "/usr/bin/python3" ]; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "No usable Python found."
  echo "Install Apple Silicon Python:"
  echo "  brew install python@3.11"
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

echo "Using: $PY"
"$PY" -c 'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}  ({sys.platform})")'
echo ""

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/5] Creating virtual environment..."
  "$PY" -m venv .venv
else
  echo "[1/5] Virtual environment already exists"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo ""
echo "[2/5] Upgrading pip..."
python -m pip install -U pip setuptools wheel

echo ""
echo "[3/5] Core packages (numpy pinned for ultralytics)..."
python -m pip install "numpy>=1.24,<2.0"
python -m pip install -r requirements.txt
python -m pip install "numpy>=1.24,<2.0"

echo ""
echo "[4/5] OSNet (Cython + tensorboard required for torchreid build)..."
python -m pip install Cython tensorboard
python -m pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git" || {
  echo ""
  echo "WARNING: OSNet install failed — body ReID will use weak fallback."
  echo "You can retry later with scripts/setup_reid.sh"
}

echo ""
echo "[5/5] Permissions + config..."
chmod +x "AI No Key.command" "Install AI No Key.command" scripts/*.sh 2>/dev/null || true
if [ ! -f config.yaml ] && [ -f config.example.yaml ]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml from example"
fi

echo ""
if python -c "from torchreid.utils import FeatureExtractor" 2>/dev/null; then
  echo "OSNet: READY"
else
  echo "OSNet: MISSING (weak fallback)"
fi
echo ""
echo "========================================"
echo "  Install complete"
echo "========================================"
echo ""
echo "Next:"
echo "  1. Double-click  AI No Key.command"
echo "  2. Wizard → UniFi host (live UNVR IP) / user / password"
echo "  3. Test connection → small sample search"
echo ""
echo "Full guide: BROTHER_SETUP.md"
echo ""
read -r -p "Press Return to close..."

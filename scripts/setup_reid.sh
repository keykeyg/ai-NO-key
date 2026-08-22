#!/usr/bin/env bash
# Install strongest body ReID: OSNet via torchreid
# Mac-safe order: numpy first, then torchreid with --no-build-isolation
set -e

echo "=== AI No Key — OSNet (strongest body ReID) ==="

# Ensure we're in a venv when possible
if [ -z "${VIRTUAL_ENV:-}" ] && [ -x ".venv/bin/python" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m pip install -U pip setuptools wheel

echo ""
echo "[1/3] Core deps (numpy first — required for torchreid build)..."
python -m pip install -U "numpy>=1.24" "torch>=2.1" "torchvision>=0.16" gdown

echo ""
echo "[2/3] torchreid (OSNet) — no build isolation so numpy is visible..."
if python -c "from torchreid.utils import FeatureExtractor" 2>/dev/null; then
  echo "  torchreid already installed — OK"
else
  python -m pip install --no-build-isolation \
    "git+https://github.com/KaiyangZhou/deep-person-reid.git" \
    || {
      echo ""
      echo "  WARNING: torchreid install failed."
      echo "  Body ReID will fall back to the weaker hand-crafted model."
      echo "  On Apple Silicon try: xcode-select --install  then re-run this script."
      exit 0
    }
fi

echo ""
echo "[3/3] Verify OSNet loads..."
python - <<'PY'
try:
    from torchreid.utils import FeatureExtractor
    print("  OSNet ready (torchreid FeatureExtractor OK)")
except Exception as e:
    print("  OSNet NOT ready:", e)
    raise SystemExit(1)
PY

echo ""
echo "Done. config should have:"
echo "  reid:"
echo "    body_method: osnet"
echo "    device: mps    # Mac Apple Silicon"

#!/usr/bin/env bash
# Install OSNet (torchreid) + optional InsightFace for AI No Key
set -e

echo "=== AI No Key ReID setup ==="

pip install -U pip
pip install -r requirements.txt

echo ""
echo "Installing torchreid (OSNet)..."
pip install gdown
pip install git+https://github.com/KaiyangZhou/deep-person-reid.git || {
  echo "torchreid install failed — body ReID will use enhanced fallback"
}

echo ""
echo "Optional: InsightFace for real face embeddings"
echo "  pip install insightface onnxruntime-gpu"
echo ""
echo "Done. Set in config.yaml:"
echo "  reid.body_method: osnet"
echo "  reid.face_backend: insightface   # only after installing insightface"

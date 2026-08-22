from __future__ import annotations

import logging
from typing import Dict, List, Optional

import cv2
import numpy as np

from .tracker import Track

logger = logging.getLogger(__name__)


def _simple_embedding(crop: np.ndarray, size: int = 64) -> np.ndarray:
    """Very lightweight appearance descriptor.

    Resize → color histogram + edge histogram.
    Good enough to bootstrap cross-camera matching until a full OSNet is wired in.
    """
    if crop is None or crop.size == 0:
        return np.zeros(96, dtype=np.float32)

    img = cv2.resize(crop, (size, size))
    # HSV color hist
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
    hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()

    # Simple edge density in 4x4 grid
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_hist = []
    step = size // 4
    for i in range(4):
        for j in range(4):
            patch = edges[i * step : (i + 1) * step, j * step : (j + 1) * step]
            edge_hist.append(patch.mean() / 255.0)

    feat = np.concatenate([hist_h, hist_s, hist_v, np.array(edge_hist, dtype=np.float32)])
    feat = feat / (np.linalg.norm(feat) + 1e-6)
    return feat.astype(np.float32)


class ReIDEmbedder:
    """Extract a single embedding vector per track."""

    def __init__(self, method: str = "simple"):
        self.method = method
        if method not in ("simple",):
            logger.warning("Only 'simple' ReID is implemented so far. Falling back.")
            self.method = "simple"

    def embed_track(self, track: Track) -> Optional[np.ndarray]:
        if not track.crops:
            return None

        embs = [_simple_embedding(c) for c in track.crops if c is not None and c.size > 0]
        if not embs:
            return None

        # Average the embeddings from the few crops we kept
        emb = np.mean(embs, axis=0)
        emb = emb / (np.linalg.norm(emb) + 1e-6)
        return emb.astype(np.float32)

    def embed_all(self, tracks: Dict[int, Track]) -> Dict[int, np.ndarray]:
        out = {}
        for tid, tr in tracks.items():
            emb = self.embed_track(tr)
            if emb is not None:
                out[tid] = emb
        return out

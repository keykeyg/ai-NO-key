from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .tracker import Track

logger = logging.getLogger(__name__)


def _enhanced_body_embedding(crop: np.ndarray, size: int = 128) -> np.ndarray:
    """Stronger appearance descriptor than basic histograms.

    Combines:
    - Multi-scale color histograms (HSV)
    - Local binary pattern-style texture summary
    - Vertical color profile (helps with clothing layers)
    - Edge orientation histogram
    """
    if crop is None or crop.size == 0:
        return np.zeros(160, dtype=np.float32)

    img = cv2.resize(crop, (size, size))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Color histograms
    h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
    v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()

    # Vertical color profile (clothing bands)
    vert = []
    band = size // 8
    for i in range(8):
        strip = hsv[i * band : (i + 1) * band, :, 0]
        vert.append(strip.mean() / 180.0)
        vert.append(strip.std() / 180.0)

    # Edge orientation (rough shape / pose cue)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    ang_hist = cv2.calcHist([ang.astype(np.uint8)], [0], None, [16], [0, 180]).flatten()
    ang_hist = ang_hist / (ang_hist.sum() + 1e-6)

    # Simple texture energy in 4x4 grid
    texture = []
    step = size // 4
    for i in range(4):
        for j in range(4):
            patch = gray[i * step : (i + 1) * step, j * step : (j + 1) * step]
            texture.append(patch.std() / 255.0)

    feat = np.concatenate([
        h / (h.sum() + 1e-6),
        s / (s.sum() + 1e-6),
        v / (v.sum() + 1e-6),
        np.array(vert, dtype=np.float32),
        ang_hist,
        np.array(texture, dtype=np.float32),
    ])
    feat = feat / (np.linalg.norm(feat) + 1e-8)
    return feat.astype(np.float32)


def _simple_face_embedding(crop: np.ndarray) -> Optional[np.ndarray]:
    """Very lightweight face cue when a dedicated face model is not installed.

    Uses the upper portion of the person crop as a proxy.
    This is intentionally weak — replace with InsightFace / similar for production.
    """
    if crop is None or crop.size == 0:
        return None
    h, w = crop.shape[:2]
    if h < 40 or w < 30:
        return None
    # Upper 35% of the body box is a rough face region
    face_region = crop[0 : int(h * 0.35), :]
    if face_region.size == 0:
        return None
    face_region = cv2.resize(face_region, (64, 64))
    hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [12, 12], [0, 180, 0, 256]).flatten()
    hist = hist / (np.linalg.norm(hist) + 1e-8)
    return hist.astype(np.float32)


class MultiModalEmbedder:
    """Produces face + body embeddings for tracks and still images."""

    def __init__(self, body_method: str = "enhanced", face_enabled: bool = True):
        self.body_method = body_method
        self.face_enabled = face_enabled
        logger.info("ReID embedder ready (body=%s, face=%s)", body_method, face_enabled)

    def embed_crop(self, crop: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        body = _enhanced_body_embedding(crop)
        face = _simple_face_embedding(crop) if self.face_enabled else None
        return face, body

    def embed_image(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """For enrollment images (assume the person is the main subject)."""
        return self.embed_crop(img)

    def embed_track(self, track: Track) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if not track.crops:
            return None, None

        face_list = []
        body_list = []
        for crop in track.crops:
            f, b = self.embed_crop(crop)
            if f is not None:
                face_list.append(f)
            if b is not None:
                body_list.append(b)

        face_e = None
        body_e = None
        if face_list:
            face_e = np.mean(face_list, axis=0)
            face_e = face_e / (np.linalg.norm(face_e) + 1e-8)
        if body_list:
            body_e = np.mean(body_list, axis=0)
            body_e = body_e / (np.linalg.norm(body_e) + 1e-8)
        return face_e, body_e

    def embed_all_tracks(self, tracks: dict) -> dict:
        """Returns {track_id: {"face": ..., "body": ...}}"""
        out = {}
        for tid, tr in tracks.items():
            face_e, body_e = self.embed_track(tr)
            out[tid] = {"face": face_e, "body": body_e}
        return out

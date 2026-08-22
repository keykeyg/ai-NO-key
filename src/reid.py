from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from .tracker import Track

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Body embedding (hand-crafted baseline)
# Replace with OSNet / Torchreid for production accuracy.
# ---------------------------------------------------------------------------

def _enhanced_body_embedding(crop: np.ndarray, size: int = 128) -> np.ndarray:
    """Appearance descriptor: color + vertical clothing bands + texture + edges."""
    if crop is None or crop.size == 0:
        return np.zeros(160, dtype=np.float32)

    img = cv2.resize(crop, (size, size))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
    s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
    v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()

    vert = []
    band = size // 8
    for i in range(8):
        strip = hsv[i * band : (i + 1) * band, :, 0]
        vert.append(float(strip.mean() / 180.0))
        vert.append(float(strip.std() / 180.0))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    _, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    ang_hist = cv2.calcHist([ang.astype(np.uint8)], [0], None, [16], [0, 180]).flatten()
    ang_hist = ang_hist / (ang_hist.sum() + 1e-6)

    texture = []
    step = size // 4
    for i in range(4):
        for j in range(4):
            patch = gray[i * step : (i + 1) * step, j * step : (j + 1) * step]
            texture.append(float(patch.std() / 255.0))

    feat = np.concatenate([
        h / (h.sum() + 1e-6),
        s / (s.sum() + 1e-6),
        v / (v.sum() + 1e-6),
        np.array(vert, dtype=np.float32),
        ang_hist.astype(np.float32),
        np.array(texture, dtype=np.float32),
    ])
    feat = feat / (np.linalg.norm(feat) + 1e-8)
    return feat.astype(np.float32)


# ---------------------------------------------------------------------------
# Face embedding
# The old "upper 35% of body box" histogram is disabled by default because it
# is not a real face embedding and causes false matches in a bar.
# When InsightFace (or similar) is installed, set face_backend="insightface".
# ---------------------------------------------------------------------------

def _try_insightface_embedding(crop: np.ndarray):
    """Optional high-quality face embedding. Returns None if not available."""
    try:
        from insightface.app import FaceAnalysis  # type: ignore
    except Exception:
        return None

    # Lazy singleton
    global _INSIGHT_APP
    if "_INSIGHT_APP" not in globals() or _INSIGHT_APP is None:
        try:
            app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(640, 640))
            _INSIGHT_APP = app
            logger.info("InsightFace loaded for face embeddings")
        except Exception as e:
            logger.warning("InsightFace init failed: %s", e)
            return None

    faces = _INSIGHT_APP.get(crop)
    if not faces:
        return None
    # Largest face
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    emb = face.normed_embedding.astype(np.float32)
    return emb


_INSIGHT_APP = None


class MultiModalEmbedder:
    """
    face + body embeddings.

    face_backend:
      - "none"         : never use face (safest with current code)
      - "insightface"  : use InsightFace if installed, else fall back to none
      - "weak"         : old upper-body histogram (NOT recommended)
    """

    def __init__(
        self,
        body_method: str = "enhanced",
        face_backend: str = "none",
        face_weight: float = 0.15,
    ):
        self.body_method = body_method
        self.face_backend = face_backend
        self.face_weight = float(face_weight)  # how much face can influence score (matcher reads this)
        logger.info(
            "ReID embedder ready (body=%s, face_backend=%s, face_weight=%.2f)",
            body_method, face_backend, face_weight,
        )

    def _face_embed(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if self.face_backend == "none":
            return None
        if self.face_backend == "insightface":
            return _try_insightface_embedding(crop)
        if self.face_backend == "weak":
            # Kept only for experiments — do not use in production
            h, w = crop.shape[:2]
            if h < 40 or w < 30:
                return None
            region = crop[0 : int(h * 0.35), :]
            if region.size == 0:
                return None
            region = cv2.resize(region, (64, 64))
            hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [12, 12], [0, 180, 0, 256]).flatten()
            return (hist / (np.linalg.norm(hist) + 1e-8)).astype(np.float32)
        return None

    def embed_crop(self, crop: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        body = _enhanced_body_embedding(crop)
        face = self._face_embed(crop)
        return face, body

    def embed_image(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return self.embed_crop(img)

    def embed_track(self, track: Track) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if not track.crops:
            return None, None
        face_list, body_list = [], []
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
        out = {}
        for tid, tr in tracks.items():
            face_e, body_e = self.embed_track(tr)
            out[tid] = {"face": face_e, "body": body_e}
        return out

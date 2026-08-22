from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .tracker import Track

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hand-crafted body embedding (fallback)
# ---------------------------------------------------------------------------

def _enhanced_body_embedding(crop: np.ndarray, size: int = 128) -> np.ndarray:
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
# OSNet via torchreid FeatureExtractor
# ---------------------------------------------------------------------------

_OSNET_EXTRACTOR = None
_OSNET_FAILED = False


def _get_osnet_extractor(device: str = "cuda"):
    """Lazy-load torchreid OSNet FeatureExtractor."""
    global _OSNET_EXTRACTOR, _OSNET_FAILED
    if _OSNET_FAILED:
        return None
    if _OSNET_EXTRACTOR is not None:
        return _OSNET_EXTRACTOR

    try:
        from torchreid.utils import FeatureExtractor  # type: ignore
    except Exception as e:
        logger.warning(
            "torchreid not installed — OSNet unavailable (%s). "
            "Install with: pip install git+https://github.com/KaiyangZhou/deep-person-reid.git", e
        )
        _OSNET_FAILED = True
        return None

    try:
        # osnet_x1_0 with ImageNet weights is enough to start; market/msmt weights improve ReID further
        # FeatureExtractor downloads/loads automatically when model_path is omitted for some builds;
        # we pass model_name and let torchreid handle pretrained ImageNet init.
        extractor = FeatureExtractor(
            model_name="osnet_x1_0",
            device=device if device else "cuda",
            verbose=False,
        )
        _OSNET_EXTRACTOR = extractor
        logger.info("OSNet (osnet_x1_0) loaded via torchreid on %s", device)
        return extractor
    except Exception as e:
        logger.warning("OSNet init failed: %s — falling back to enhanced hand-crafted body embedding", e)
        _OSNET_FAILED = True
        return None


def _osnet_embed_bgr(crop: np.ndarray, device: str = "cuda") -> Optional[np.ndarray]:
    """Embed a single BGR crop with OSNet. Returns L2-normalized 512-d vector."""
    extractor = _get_osnet_extractor(device=device)
    if extractor is None or crop is None or crop.size == 0:
        return None
    try:
        # torchreid FeatureExtractor expects RGB numpy or path; convert BGR→RGB
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        feats = extractor([rgb])  # shape (1, 512)
        if feats is None:
            return None
        if hasattr(feats, "cpu"):
            feats = feats.cpu().numpy()
        vec = np.asarray(feats[0], dtype=np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-8)
        return vec
    except Exception as e:
        logger.debug("OSNet embed failed on crop: %s", e)
        return None


def _osnet_embed_batch_bgr(crops: List[np.ndarray], device: str = "cuda") -> List[Optional[np.ndarray]]:
    extractor = _get_osnet_extractor(device=device)
    if extractor is None:
        return [None] * len(crops)
    valid_idx = []
    rgb_list = []
    for i, c in enumerate(crops):
        if c is None or c.size == 0:
            continue
        valid_idx.append(i)
        rgb_list.append(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
    out: List[Optional[np.ndarray]] = [None] * len(crops)
    if not rgb_list:
        return out
    try:
        feats = extractor(rgb_list)
        if hasattr(feats, "cpu"):
            feats = feats.cpu().numpy()
        for j, i in enumerate(valid_idx):
            vec = np.asarray(feats[j], dtype=np.float32)
            out[i] = vec / (np.linalg.norm(vec) + 1e-8)
    except Exception as e:
        logger.debug("OSNet batch embed failed: %s", e)
    return out


# ---------------------------------------------------------------------------
# Optional InsightFace
# ---------------------------------------------------------------------------

_INSIGHT_APP = None
_INSIGHT_FAILED = False


def _try_insightface_embedding(crop: np.ndarray) -> Optional[np.ndarray]:
    global _INSIGHT_APP, _INSIGHT_FAILED
    if _INSIGHT_FAILED:
        return None
    try:
        from insightface.app import FaceAnalysis  # type: ignore
    except Exception:
        _INSIGHT_FAILED = True
        return None

    if _INSIGHT_APP is None:
        try:
            app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(640, 640))
            _INSIGHT_APP = app
            logger.info("InsightFace loaded")
        except Exception as e:
            logger.warning("InsightFace init failed: %s", e)
            _INSIGHT_FAILED = True
            return None

    faces = _INSIGHT_APP.get(crop)
    if not faces:
        return None
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding.astype(np.float32)


# ---------------------------------------------------------------------------
# Public embedder
# ---------------------------------------------------------------------------

class MultiModalEmbedder:
    """
    body_method:
      - "osnet"     : torchreid OSNet (recommended) — falls back to enhanced if missing
      - "enhanced" : hand-crafted histogram/texture baseline
    face_backend:
      - "none" | "insightface" | "weak"
    """

    def __init__(
        self,
        body_method: str = "osnet",
        face_backend: str = "none",
        face_weight: float = 0.15,
        device: str = "cuda",
    ):
        self.body_method = body_method
        self.face_backend = face_backend
        self.face_weight = float(face_weight)
        self.device = device

        if body_method == "osnet":
            ext = _get_osnet_extractor(device=device)
            if ext is None:
                logger.warning("OSNet requested but unavailable — using enhanced body embedding")
                self.body_method = "enhanced"

        logger.info(
            "ReID ready (body=%s, face=%s, face_weight=%.2f, device=%s)",
            self.body_method, face_backend, face_weight, device,
        )

    def _body_embed(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if self.body_method == "osnet":
            vec = _osnet_embed_bgr(crop, device=self.device)
            if vec is not None:
                return vec
            # soft fallback per-crop
            return _enhanced_body_embedding(crop)
        return _enhanced_body_embedding(crop)

    def _face_embed(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if self.face_backend == "none":
            return None
        if self.face_backend == "insightface":
            return _try_insightface_embedding(crop)
        if self.face_backend == "weak":
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
        body = self._body_embed(crop)
        face = self._face_embed(crop)
        return face, body

    def embed_image(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return self.embed_crop(img)

    def embed_track(self, track: Track) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if not track.crops:
            return None, None

        if self.body_method == "osnet":
            body_list = _osnet_embed_batch_bgr(track.crops, device=self.device)
            body_list = [b for b in body_list if b is not None]
            if not body_list:
                body_list = [_enhanced_body_embedding(c) for c in track.crops if c is not None and c.size > 0]
        else:
            body_list = [_enhanced_body_embedding(c) for c in track.crops if c is not None and c.size > 0]

        face_list = []
        if self.face_backend != "none":
            for c in track.crops:
                f = self._face_embed(c)
                if f is not None:
                    face_list.append(f)

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

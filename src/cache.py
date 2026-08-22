from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .tracker import Track
from .utils import ensure_dir

logger = logging.getLogger(__name__)


def _emb_to_serializable(emb_map: Dict[int, dict]) -> Dict[str, dict]:
    out = {}
    for tid, d in emb_map.items():
        out[str(tid)] = {
            "face": d["face"].tolist() if d.get("face") is not None else None,
            "body": d["body"].tolist() if d.get("body") is not None else None,
        }
    return out


def _emb_from_serializable(raw: Dict[str, dict]) -> Dict[int, dict]:
    out = {}
    for tid_s, d in raw.items():
        face = np.array(d["face"], dtype=np.float32) if d.get("face") is not None else None
        body = np.array(d["body"], dtype=np.float32) if d.get("body") is not None else None
        out[int(tid_s)] = {"face": face, "body": body}
    return out


class DetectionCache:
    """
    Persist tracks + embeddings so follow_person does not re-run YOLO every time.

    Layout:
      output_dir/cache/
        meta.json
        <camera>.pkl          # tracks (with crops)
        <camera>_emb.json     # embeddings only (lightweight)
    """

    def __init__(self, output_dir: str | Path):
        self.root = ensure_dir(Path(output_dir) / "cache")

    def meta_path(self) -> Path:
        return self.root / "meta.json"

    def track_path(self, camera: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in camera)
        return self.root / f"{safe}.pkl"

    def emb_path(self, camera: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in camera)
        return self.root / f"{safe}_emb.json"

    def save_camera(self, camera: str, tracks: Dict[int, Track], embeddings: Dict[int, dict]) -> None:
        with open(self.track_path(camera), "wb") as f:
            pickle.dump(tracks, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(self.emb_path(camera), "w", encoding="utf-8") as f:
            json.dump(_emb_to_serializable(embeddings), f)
        logger.info("Cached %s: %d tracks", camera, len(tracks))

    def load_camera(self, camera: str) -> Optional[Tuple[Dict[int, Track], Dict[int, dict]]]:
        tp = self.track_path(camera)
        ep = self.emb_path(camera)
        if not tp.exists() or not ep.exists():
            return None
        with open(tp, "rb") as f:
            tracks = pickle.load(f)
        with open(ep, "r", encoding="utf-8") as f:
            emb = _emb_from_serializable(json.load(f))
        return tracks, emb

    def save_meta(self, cameras: list, total_tracks: int) -> None:
        meta = {"cameras": cameras, "num_tracks_total": total_tracks}
        with open(self.meta_path(), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def load_all(self) -> Optional[Dict[str, Any]]:
        if not self.meta_path().exists():
            return None
        with open(self.meta_path(), "r", encoding="utf-8") as f:
            meta = json.load(f)
        all_tracks = {}
        all_emb = {}
        for cam in meta.get("cameras", []):
            loaded = self.load_camera(cam)
            if loaded is None:
                logger.warning("Cache incomplete for camera %s — full re-run needed", cam)
                return None
            tracks, emb = loaded
            all_tracks[cam] = tracks
            all_emb[cam] = emb
        logger.info("Loaded detection cache: %d cameras, %d tracks",
                    len(all_tracks), sum(len(t) for t in all_tracks.values()))
        return {"tracks": all_tracks, "embeddings": all_emb, "cameras": meta["cameras"]}

    def exists(self) -> bool:
        return self.meta_path().exists()

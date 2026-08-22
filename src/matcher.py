from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from .tracker import Track

logger = logging.getLogger(__name__)


@dataclass
class GlobalPerson:
    global_id: int
    tracks: List[Tuple[str, int]] = field(default_factory=list)  # (camera, local_track_id)
    embeddings: List[np.ndarray] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0

    def add(self, camera: str, local_id: int, emb: np.ndarray, t0: float, t1: float):
        self.tracks.append((camera, local_id))
        self.embeddings.append(emb)
        if not self.first_seen:
            self.first_seen = t0
        self.first_seen = min(self.first_seen, t0)
        self.last_seen = max(self.last_seen, t1)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


class CrossCameraMatcher:
    """Greedy + Hungarian matching of local tracks into global identities."""

    def __init__(
        self,
        match_threshold: float = 0.55,
        max_time_gap_seconds: float = 300.0,
    ):
        self.match_threshold = match_threshold
        self.max_time_gap = max_time_gap_seconds
        self.next_gid = 1

    def match(
        self,
        camera_tracks: Dict[str, Dict[int, Track]],
        embeddings: Dict[str, Dict[int, np.ndarray]],
    ) -> Dict[int, GlobalPerson]:
        """
        camera_tracks: {cam_name: {local_id: Track}}
        embeddings:    {cam_name: {local_id: emb}}
        """
        # Flatten all local tracks that have an embedding
        items: List[Tuple[str, int, Track, np.ndarray]] = []
        for cam, tracks in camera_tracks.items():
            emb_map = embeddings.get(cam, {})
            for lid, tr in tracks.items():
                if lid in emb_map:
                    items.append((cam, lid, tr, emb_map[lid]))

        if not items:
            logger.warning("No tracks with embeddings to match")
            return {}

        # Sort by first appearance time so we can do online-ish assignment
        items.sort(key=lambda x: x[2].timestamps[0] if x[2].timestamps else 0.0)

        globals_: Dict[int, GlobalPerson] = {}
        # Keep a list of active global prototypes: (gid, mean_emb, last_seen)
        active: List[Tuple[int, np.ndarray, float]] = []

        for cam, lid, tr, emb in items:
            t0 = tr.timestamps[0] if tr.timestamps else 0.0
            t1 = tr.timestamps[-1] if tr.timestamps else t0

            best_gid = None
            best_score = -1.0

            for gid, mean_emb, last_seen in active:
                if t0 - last_seen > self.max_time_gap:
                    continue
                score = cosine_similarity(emb, mean_emb)
                if score > best_score:
                    best_score = score
                    best_gid = gid

            if best_gid is not None and best_score >= self.match_threshold:
                gp = globals_[best_gid]
                gp.add(cam, lid, emb, t0, t1)
                # Update prototype
                new_mean = np.mean(gp.embeddings, axis=0)
                new_mean = new_mean / (np.linalg.norm(new_mean) + 1e-6)
                # replace in active list
                active = [
                    (gid, new_mean if gid == best_gid else e, t1 if gid == best_gid else ls)
                    for gid, e, ls in active
                ]
            else:
                # New global identity
                gid = self.next_gid
                self.next_gid += 1
                gp = GlobalPerson(global_id=gid)
                gp.add(cam, lid, emb, t0, t1)
                globals_[gid] = gp
                active.append((gid, emb.copy(), t1))

        logger.info("Created %d global identities from %d local tracks", len(globals_), len(items))
        return globals_

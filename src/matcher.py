from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .profiles import StaffProfile
from .topology import CameraTopology
from .tracker import Track

logger = logging.getLogger(__name__)


def cosine(a: Optional[np.ndarray], b: Optional[np.ndarray]) -> float:
    if a is None or b is None:
        return -1.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


@dataclass
class LinkedAppearance:
    camera: str
    local_id: int
    start_s: float
    end_s: float
    score: float
    track: Track


@dataclass
class PersonTrail:
    name: str
    appearances: List[LinkedAppearance] = field(default_factory=list)

    def sorted_appearances(self) -> List[LinkedAppearance]:
        return sorted(self.appearances, key=lambda a: a.start_s)


class SeedMatcher:
    """Match local tracks against a seed (profile or live track)."""

    def __init__(
        self,
        topology: CameraTopology,
        match_threshold: float = 0.52,
        strong_threshold: float = 0.68,
        max_time_gap: float = 420.0,
    ):
        self.topology = topology
        self.match_threshold = match_threshold
        self.strong_threshold = strong_threshold
        self.max_time_gap = max_time_gap

    def _score(
        self,
        seed_face: Optional[np.ndarray],
        seed_body: Optional[np.ndarray],
        cand_face: Optional[np.ndarray],
        cand_body: Optional[np.ndarray],
    ) -> float:
        face_s = cosine(seed_face, cand_face)
        body_s = cosine(seed_body, cand_body)

        # Prefer face when both are strong, otherwise lean on body
        if face_s > 0.6 and body_s > 0.4:
            return 0.55 * face_s + 0.45 * body_s
        if face_s > 0.55:
            return 0.7 * face_s + 0.3 * max(body_s, 0.0)
        if body_s > 0.0:
            return body_s
        return -1.0

    def follow_seed(
        self,
        seed_face: Optional[np.ndarray],
        seed_body: Optional[np.ndarray],
        seed_camera: str,
        seed_time: float,
        all_tracks: Dict[str, Dict[int, Track]],
        all_embeddings: Dict[str, Dict[int, dict]],
        name: str = "target",
    ) -> PersonTrail:
        """Build a continuous trail starting from the seed."""
        trail = PersonTrail(name=name)
        candidates: List[Tuple[float, str, int, Track, float]] = []  # (start, cam, lid, track, score)

        for cam, tracks in all_tracks.items():
            emb_map = all_embeddings.get(cam, {})
            for lid, tr in tracks.items():
                emb = emb_map.get(lid, {})
                score = self._score(seed_face, seed_body, emb.get("face"), emb.get("body"))
                if score < self.match_threshold:
                    continue
                t0, t1 = tr.start_end()
                # Basic temporal reasonableness from seed
                if t1 < seed_time - 30:  # appeared well before seed — skip for forward trail
                    continue
                gap = abs(t0 - seed_time)
                if gap > self.max_time_gap and cam != seed_camera:
                    # still allow strong matches
                    if score < self.strong_threshold:
                        continue
                if not self.topology.is_plausible(seed_camera, cam, gap):
                    if score < self.strong_threshold:
                        continue
                candidates.append((t0, cam, lid, tr, score))

        candidates.sort(key=lambda x: x[0])

        # Greedy chain: prefer high score + topology + time order
        last_cam = seed_camera
        last_time = seed_time
        used = set()

        for t0, cam, lid, tr, score in candidates:
            key = (cam, lid)
            if key in used:
                continue
            gap = t0 - last_time
            if gap < -5:
                continue
            if not self.topology.is_plausible(last_cam, cam, max(gap, 0)):
                if score < self.strong_threshold:
                    continue

            t0, t1 = tr.start_end()
            trail.appearances.append(
                LinkedAppearance(
                    camera=cam,
                    local_id=lid,
                    start_s=t0,
                    end_s=t1,
                    score=score,
                    track=tr,
                )
            )
            used.add(key)
            last_cam = cam
            last_time = t1

        logger.info("Trail '%s': %d linked appearances", name, len(trail.appearances))
        return trail

    def follow_profile(
        self,
        profile: StaffProfile,
        all_tracks: Dict[str, Dict[int, Track]],
        all_embeddings: Dict[str, Dict[int, dict]],
    ) -> PersonTrail:
        seed_face = profile.mean_face()
        seed_body = profile.mean_body()
        # Use earliest strong match as the effective seed time/camera
        best = None
        best_score = -1.0
        for cam, tracks in all_tracks.items():
            emb_map = all_embeddings.get(cam, {})
            for lid, tr in tracks.items():
                emb = emb_map.get(lid, {})
                score = self._score(seed_face, seed_body, emb.get("face"), emb.get("body"))
                if score > best_score:
                    best_score = score
                    best = (cam, tr.start_end()[0], score)
        if best is None or best_score < self.match_threshold:
            logger.warning("No strong match found for profile %s", profile.name)
            return PersonTrail(name=profile.name)

        seed_cam, seed_t, _ = best
        return self.follow_seed(
            seed_face, seed_body, seed_cam, seed_t,
            all_tracks, all_embeddings, name=profile.name,
        )

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
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-8 or nb < 1e-8:
        return -1.0
    return float(np.dot(a, b) / (na * nb))


def confidence_tier(score: float, strong_threshold: float, match_threshold: float) -> str:
    if score >= strong_threshold:
        return "strong"
    if score >= match_threshold:
        return "possible"
    return "weak"


@dataclass
class LinkedAppearance:
    camera: str
    local_id: int
    start_s: float
    end_s: float
    score: float
    track: Track
    confidence: str = "possible"


@dataclass
class PersonTrail:
    name: str
    appearances: List[LinkedAppearance] = field(default_factory=list)

    def sorted_appearances(self) -> List[LinkedAppearance]:
        return sorted(self.appearances, key=lambda a: a.start_s)


class SeedMatcher:
    def __init__(
        self,
        topology: CameraTopology,
        match_threshold: float = 0.52,
        strong_threshold: float = 0.68,
        max_time_gap: float = 420.0,
        face_weight: float = 0.15,
    ):
        self.topology = topology
        self.match_threshold = match_threshold
        self.strong_threshold = strong_threshold
        self.max_time_gap = max_time_gap
        self.face_weight = face_weight

    def _score(
        self,
        seed_face: Optional[np.ndarray],
        seed_body: Optional[np.ndarray],
        cand_face: Optional[np.ndarray],
        cand_body: Optional[np.ndarray],
    ) -> float:
        body_s = cosine(seed_body, cand_body)
        face_s = cosine(seed_face, cand_face)

        if body_s < 0 and face_s < 0:
            return -1.0

        if body_s < 0:
            body_s = 0.0
        if face_s > 0.7 and self.face_weight > 0:
            return (1.0 - self.face_weight) * body_s + self.face_weight * face_s
        return body_s

    def _gap_penalty(self, gap_seconds: float) -> float:
        if gap_seconds <= 30:
            return 1.0
        if gap_seconds <= 90:
            return 0.95
        if gap_seconds <= 180:
            return 0.85
        if gap_seconds <= 300:
            return 0.70
        return 0.55

    def _required_score(self, cam_a: str, cam_b: str, gap: float) -> float:
        base = self.match_threshold
        if cam_a == cam_b:
            return base
        if not self.topology.is_plausible(cam_a, cam_b, max(gap, 0)):
            return self.strong_threshold
        if gap > 180:
            return max(base + 0.08, self.match_threshold)
        if gap > 90:
            return max(base + 0.04, self.match_threshold)
        return base

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
        trail = PersonTrail(name=name)
        scored: List[Tuple[float, float, str, int, Track]] = []

        for cam, tracks in all_tracks.items():
            emb_map = all_embeddings.get(cam, {})
            for lid, tr in tracks.items():
                emb = emb_map.get(lid, {})
                raw = self._score(seed_face, seed_body, emb.get("face"), emb.get("body"))
                if raw < self.match_threshold * 0.9:
                    continue
                t0, t1 = tr.start_end()
                if t1 < seed_time - 20:
                    continue
                gap_from_seed = max(0.0, t0 - seed_time)
                if gap_from_seed > self.max_time_gap and raw < self.strong_threshold:
                    continue
                eff = raw * self._gap_penalty(gap_from_seed)
                scored.append((eff, t0, cam, lid, tr))

        scored.sort(key=lambda x: (-x[0], x[1]))

        last_cam = seed_camera
        last_time = seed_time
        used = set()
        accepted: List[Tuple[float, str, int, Track, float]] = []

        for eff, t0, cam, lid, tr in scored:
            key = (cam, lid)
            if key in used:
                continue
            gap = t0 - last_time
            if gap < -10:
                continue
            need = self._required_score(last_cam, cam, max(gap, 0))
            raw = self._score(
                seed_face, seed_body,
                all_embeddings.get(cam, {}).get(lid, {}).get("face"),
                all_embeddings.get(cam, {}).get(lid, {}).get("body"),
            )
            if raw < need:
                continue
            if not self.topology.is_plausible(last_cam, cam, max(gap, 0)) and raw < self.strong_threshold:
                continue

            t0, t1 = tr.start_end()
            accepted.append((t0, cam, lid, tr, raw))
            used.add(key)
            last_cam = cam
            last_time = t1

        accepted.sort(key=lambda x: x[0])
        for t0, cam, lid, tr, raw in accepted:
            t0, t1 = tr.start_end()
            trail.appearances.append(
                LinkedAppearance(
                    camera=cam,
                    local_id=lid,
                    start_s=t0,
                    end_s=t1,
                    score=raw,
                    track=tr,
                    confidence=confidence_tier(raw, self.strong_threshold, self.match_threshold),
                )
            )

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
            logger.warning("No strong match found for profile %s (best=%.3f)", profile.name, best_score)
            return PersonTrail(name=profile.name)

        seed_cam, seed_t, _ = best
        return self.follow_seed(
            seed_face, seed_body, seed_cam, seed_t,
            all_tracks, all_embeddings, name=profile.name,
        )

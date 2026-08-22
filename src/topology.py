from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class CameraTopology:
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", True)
        self.max_transition_seconds = float(config.get("max_transition_seconds", 180))
        self.cameras: List[str] = list(config.get("cameras", []))
        raw = config.get("transitions", {})

        self.adj: Dict[str, Set[str]] = {c: set() for c in self.cameras}
        for src, dsts in raw.items():
            if src not in self.adj:
                self.adj[src] = set()
            for d in dsts:
                self.adj[src].add(d)
                if d not in self.adj:
                    self.adj[d] = set()
                self.adj[d].add(src)

        if self.enabled:
            logger.info(
                "Topology loaded: %d cameras, %d edges",
                len(self.adj),
                sum(len(v) for v in self.adj.values()) // 2,
            )

    def validate_against_disk(self, disk_cameras: List[str]) -> None:
        """Warn if topology names don't match actual camera folders."""
        disk = set(disk_cameras)
        topo = set(self.cameras)
        missing_on_disk = topo - disk
        missing_in_topo = disk - topo
        if missing_on_disk:
            logger.warning(
                "Topology lists cameras not found on disk: %s",
                sorted(missing_on_disk),
            )
        if missing_in_topo:
            logger.warning(
                "Cameras on disk not listed in topology (transitions will be permissive): %s",
                sorted(missing_in_topo),
            )
        if not missing_on_disk and not missing_in_topo and self.cameras:
            logger.info("Topology camera names match disk folders")

    def is_plausible(self, cam_a: str, cam_b: str, time_gap: float) -> bool:
        if not self.enabled:
            return True
        if cam_a == cam_b:
            return True
        if time_gap > self.max_transition_seconds * 3:
            return False
        if cam_a not in self.adj or cam_b not in self.adj:
            return time_gap <= self.max_transition_seconds * 2
        if cam_b in self.adj.get(cam_a, set()):
            return time_gap <= self.max_transition_seconds
        neighbors = self.adj.get(cam_a, set())
        for n in neighbors:
            if cam_b in self.adj.get(n, set()):
                return time_gap <= self.max_transition_seconds * 1.8
        return time_gap <= self.max_transition_seconds * 0.7

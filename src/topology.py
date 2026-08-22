from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CameraTopology:
    """Simple undirected graph of plausible camera transitions."""

    def __init__(self, config: dict):
        self.enabled = config.get("enabled", True)
        self.max_transition_seconds = float(config.get("max_transition_seconds", 180))
        self.cameras: List[str] = list(config.get("cameras", []))
        raw = config.get("transitions", {})

        # Build adjacency (undirected)
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
            logger.info("Topology loaded: %d cameras, %d edges",
                        len(self.adj),
                        sum(len(v) for v in self.adj.values()) // 2)

    def is_plausible(self, cam_a: str, cam_b: str, time_gap: float) -> bool:
        """Return True if moving from cam_a to cam_b in `time_gap` seconds is reasonable."""
        if not self.enabled:
            return True
        if cam_a == cam_b:
            return True
        if time_gap > self.max_transition_seconds * 3:  # hard upper bound
            return False
        # If we have no topology info for these cameras, be permissive
        if cam_a not in self.adj or cam_b not in self.adj:
            return time_gap <= self.max_transition_seconds * 2
        # Direct neighbor
        if cam_b in self.adj.get(cam_a, set()):
            return time_gap <= self.max_transition_seconds
        # Allow one-hop if the gap is larger
        neighbors = self.adj.get(cam_a, set())
        for n in neighbors:
            if cam_b in self.adj.get(n, set()):
                return time_gap <= self.max_transition_seconds * 1.8
        # Unknown path — still allow with strict time
        return time_gap <= self.max_transition_seconds * 0.7

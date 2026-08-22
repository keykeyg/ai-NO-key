from __future__ import annotations

import logging
from typing import List, Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


class PersonDetector:
    """Thin wrapper around Ultralytics YOLO focused on people."""

    def __init__(
        self,
        model_name: str = "yolo11m.pt",
        conf: float = 0.4,
        classes: Optional[List[int]] = None,
        device: str = "0",
    ):
        self.model = YOLO(model_name)
        self.conf = conf
        self.classes = classes if classes is not None else [0]  # person
        self.device = device
        logger.info("Loaded detector %s on device %s", model_name, device)

    def track(
        self,
        source,
        tracker: str = "bytetrack.yaml",
        persist: bool = True,
        stream: bool = True,
        **kwargs,
    ):
        """Run tracking. Returns a generator of Results when stream=True."""
        return self.model.track(
            source=source,
            conf=self.conf,
            classes=self.classes,
            tracker=tracker,
            persist=persist,
            stream=stream,
            device=self.device,
            verbose=False,
            **kwargs,
        )

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics.engine.results import Results

from .detector import PersonDetector

logger = logging.getLogger(__name__)


@dataclass
class Track:
    track_id: int
    camera: str
    frames: List[int] = field(default_factory=list)
    boxes: List[Tuple[float, float, float, float]] = field(default_factory=list)  # xyxy
    confs: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)  # seconds from start of video
    crops: List[np.ndarray] = field(default_factory=list)  # optional small crops for ReID

    def duration(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0
        return self.timestamps[-1] - self.timestamps[0]

    def mean_box(self) -> Tuple[float, float, float, float]:
        arr = np.array(self.boxes)
        return tuple(arr.mean(axis=0).tolist())


class CameraTracker:
    """Process one camera's video(s) and collect local tracks."""

    def __init__(
        self,
        detector: PersonDetector,
        tracker_cfg: str = "bytetrack.yaml",
        frame_skip: int = 1,
        save_crops: bool = True,
        max_crops_per_track: int = 8,
    ):
        self.detector = detector
        self.tracker_cfg = tracker_cfg
        self.frame_skip = max(1, frame_skip)
        self.save_crops = save_crops
        self.max_crops_per_track = max_crops_per_track

    def process_video(
        self,
        video_path: str | Path,
        camera_name: str,
    ) -> Dict[int, Track]:
        video_path = Path(video_path)
        logger.info("Tracking %s (%s)", camera_name, video_path.name)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        cap.release()

        tracks: Dict[int, Track] = {}
        frame_idx = 0

        # Ultralytics handles the video file directly and keeps tracker state
        results_gen = self.detector.track(
            source=str(video_path),
            tracker=self.tracker_cfg,
            persist=True,
            stream=True,
            vid_stride=self.frame_skip,
        )

        for result in results_gen:
            if result.boxes is None or result.boxes.id is None:
                frame_idx += self.frame_skip
                continue

            boxes = result.boxes.xyxy.cpu().numpy()
            ids = result.boxes.id.int().cpu().tolist()
            confs = result.boxes.conf.cpu().numpy()

            # Approximate time from frame index
            t = frame_idx / fps

            for box, tid, conf in zip(boxes, ids, confs):
                if tid not in tracks:
                    tracks[tid] = Track(track_id=tid, camera=camera_name)

                tr = tracks[tid]
                tr.frames.append(frame_idx)
                tr.boxes.append(tuple(map(float, box)))
                tr.confs.append(float(conf))
                tr.timestamps.append(t)

                if self.save_crops and len(tr.crops) < self.max_crops_per_track:
                    # result.orig_img is the current frame
                    img = result.orig_img
                    if img is not None:
                        x1, y1, x2, y2 = map(int, box)
                        h, w = img.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        if x2 > x1 and y2 > y1:
                            crop = img[y1:y2, x1:x2].copy()
                            tr.crops.append(crop)

            frame_idx += self.frame_skip

        logger.info(
            "Camera %s: %d tracks from %s (approx %d frames)",
            camera_name,
            len(tracks),
            video_path.name,
            total_frames,
        )
        return tracks

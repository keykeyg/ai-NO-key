from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .timerange import parse_seconds
from .utils import ensure_dir

logger = logging.getLogger(__name__)


def grab_frame(video_path: str | Path, at) -> Tuple[np.ndarray, float]:
    """Grab a frame at seconds or HH:MM:SS into the video."""
    t = parse_seconds(at)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_idx = int(max(0, t) * fps)
    if total:
        frame_idx = min(frame_idx, max(0, total - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"Could not read frame at {t:.2f}s in {video_path}")
    return frame, frame_idx / fps


def detect_people(frame: np.ndarray, model_name: str = "yolo11n.pt", conf: float = 0.35) -> List[dict]:
    from ultralytics import YOLO

    model = YOLO(model_name)
    results = model.predict(frame, classes=[0], conf=conf, verbose=False)
    people = []
    if not results or results[0].boxes is None:
        return people
    boxes = results[0].boxes.xyxy.cpu().numpy()
    scores = results[0].boxes.conf.cpu().numpy()
    h, w = frame.shape[:2]
    for i, (box, score) in enumerate(zip(boxes, scores)):
        x1, y1, x2, y2 = map(int, box)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = frame[y1:y2, x1:x2].copy()
        people.append({
            "index": i,
            "box": [x1, y1, x2, y2],
            "conf": float(score),
            "area": (x2 - x1) * (y2 - y1),
            "crop": crop,
        })
    people.sort(key=lambda p: -p["area"])
    for i, p in enumerate(people):
        p["index"] = i
    return people


def annotate(frame: np.ndarray, people: List[dict]) -> np.ndarray:
    out = frame.copy()
    for p in people:
        x1, y1, x2, y2 = p["box"]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 220, 120), 2)
        label = f"#{p['index']}  {p['conf']:.2f}"
        cv2.putText(out, label, (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 120), 2)
    return out


def save_tag_session(
    video_path: str | Path,
    at,
    out_dir: str | Path,
    model_name: str = "yolo11n.pt",
) -> dict:
    """Detect people at a timestamp, save overview + numbered crops."""
    frame, actual_t = grab_frame(video_path, at)
    people = detect_people(frame, model_name=model_name)
    dest = ensure_dir(out_dir)
    overview = dest / "overview.jpg"
    cv2.imwrite(str(overview), annotate(frame, people))
    crops = []
    for p in people:
        crop_path = dest / f"crop_{p['index']:02d}.jpg"
        cv2.imwrite(str(crop_path), p["crop"])
        crops.append({
            "index": p["index"],
            "path": str(crop_path),
            "conf": round(p["conf"], 3),
            "box": p["box"],
        })
    return {
        "video": str(video_path),
        "at_s": round(actual_t, 2),
        "overview": str(overview),
        "num_people": len(people),
        "crops": crops,
        "people": people,
    }

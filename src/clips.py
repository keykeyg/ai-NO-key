from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2

from .tracker import Track

logger = logging.getLogger(__name__)


def extract_track_clip(
    track: Track,
    output_path: str | Path,
    padding_seconds: float = 1.5,
    max_duration: float = 40.0,
    draw_box: bool = True,
) -> Optional[Path]:
    if not track.video_path or not track.timestamps or not track.frames:
        return None

    video_path = Path(track.video_path)
    if not video_path.exists():
        logger.warning("Source video missing: %s", video_path)
        return None

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    t0, t1 = track.start_end()
    start_t = max(0.0, t0 - padding_seconds)
    end_t = min(t1 + padding_seconds, total_frames / fps)
    if end_t - start_t > max_duration:
        end_t = start_t + max_duration

    start_frame = int(start_t * fps)
    end_frame = int(end_t * fps)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_to_box = {f: b for f, b in zip(track.frames, track.boxes)}

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current = start_frame
    while current <= end_frame:
        ok, frame = cap.read()
        if not ok:
            break
        if draw_box and current in frame_to_box:
            x1, y1, x2, y2 = map(int, frame_to_box[current])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 80), 2)
            cv2.putText(frame, f"ID {track.track_id}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 80), 2)
        writer.write(frame)
        current += 1

    writer.release()
    cap.release()
    return output_path


def extract_person_clips(
    global_id: int,
    track_refs: List[Tuple[str, int]],
    all_tracks: Dict[str, Dict[int, Track]],
    clips_dir: Path,
    padding_seconds: float = 1.5,
) -> List[Dict]:
    results = []
    clips_dir = Path(clips_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)

    for cam, lid in track_refs:
        tr = all_tracks.get(cam, {}).get(lid)
        if tr is None:
            continue
        out = clips_dir / f"{cam}_local{lid}.mp4"
        path = extract_track_clip(tr, out, padding_seconds=padding_seconds)
        if path:
            results.append({
                "camera": cam,
                "local_id": lid,
                "clip": str(path.name),
                "start_s": round(tr.start_end()[0], 1),
                "end_s": round(tr.start_end()[1], 1),
                "duration_s": round(tr.duration(), 1),
            })
    return results

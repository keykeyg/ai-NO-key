from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from .clips import extract_person_clips
from .detector import PersonDetector
from .matcher import CrossCameraMatcher
from .reid import ReIDEmbedder
from .tracker import CameraTracker
from .utils import ensure_dir, list_camera_videos, save_json

logger = logging.getLogger(__name__)


class OvernightPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.output_dir = ensure_dir(config["output_dir"])

        self.detector = PersonDetector(
            model_name=config.get("model", "yolo11m.pt"),
            conf=config.get("conf", 0.4),
            classes=config.get("classes", [0]),
        )
        self.camera_tracker = CameraTracker(
            detector=self.detector,
            tracker_cfg=config.get("tracker", "bytetrack.yaml"),
            frame_skip=config.get("frame_skip", 2),
            save_crops=True,
        )
        reid_cfg = config.get("reid", {})
        self.embedder = ReIDEmbedder(method=reid_cfg.get("method", "simple"))
        self.matcher = CrossCameraMatcher(
            match_threshold=reid_cfg.get("match_threshold", 0.55),
            max_time_gap_seconds=reid_cfg.get("max_time_gap_seconds", 300),
        )
        self.save_track_clips = config.get("save_track_clips", True)

    def run(self) -> Dict[str, Any]:
        cameras = list_camera_videos(self.cfg["cameras_root"])
        if not cameras:
            raise RuntimeError(f"No camera videos found under {self.cfg['cameras_root']}")

        logger.info("Found %d cameras", len(cameras))

        all_tracks: Dict[str, Dict] = {}
        all_embeddings: Dict[str, Dict] = {}

        for cam_name, videos in cameras.items():
            cam_tracks = {}
            for video in videos:
                tracks = self.camera_tracker.process_video(video, cam_name)
                offset = max(cam_tracks.keys(), default=0)
                for lid, tr in tracks.items():
                    new_id = lid + offset
                    tr.track_id = new_id
                    cam_tracks[new_id] = tr

            embs = self.embedder.embed_all(cam_tracks)
            all_tracks[cam_name] = cam_tracks
            all_embeddings[cam_name] = embs

            summary = {
                "camera": cam_name,
                "num_tracks": len(cam_tracks),
                "tracks": [
                    {
                        "local_id": tid,
                        "duration_s": round(tr.duration(), 1),
                        "num_frames": len(tr.frames),
                        "first_seen": round(tr.timestamps[0], 1) if tr.timestamps else None,
                        "last_seen": round(tr.timestamps[-1], 1) if tr.timestamps else None,
                        "video": tr.video_path,
                    }
                    for tid, tr in cam_tracks.items()
                ],
            }
            save_json(summary, self.output_dir / "per_camera" / f"{cam_name}.json")

        globals_ = self.matcher.match(all_tracks, all_embeddings)

        clips_dir = ensure_dir(self.output_dir / "clips")
        report = {
            "num_cameras": len(cameras),
            "num_global_people": len(globals_),
            "people": [],
        }

        for gid, gp in sorted(globals_.items()):
            person = {
                "global_id": gid,
                "cameras_seen": sorted({c for c, _ in gp.tracks}),
                "num_local_tracks": len(gp.tracks),
                "first_seen": round(gp.first_seen, 1),
                "last_seen": round(gp.last_seen, 1),
                "track_refs": [{"camera": c, "local_id": lid} for c, lid in gp.tracks],
                "clips": [],
            }

            if self.save_track_clips:
                clip_infos = extract_person_clips(
                    global_id=gid,
                    track_refs=gp.tracks,
                    all_tracks=all_tracks,
                    clips_dir=clips_dir,
                )
                person["clips"] = clip_infos

            report["people"].append(person)

        save_json(report, self.output_dir / "global_report.json")
        logger.info("Wrote global report → %s", self.output_dir / "global_report.json")
        logger.info("Found %d unique people across all cameras", len(globals_))
        return report

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from .cache import DetectionCache
from .clips import extract_person_clips
from .detector import PersonDetector
from .device import resolve_device
from .matcher import SeedMatcher
from .profiles import ProfileStore
from .reid import MultiModalEmbedder
from .topology import CameraTopology
from .tracker import CameraTracker, Track
from .utils import ensure_dir, list_camera_videos, save_json

logger = logging.getLogger(__name__)


class OvernightPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.output_dir = ensure_dir(config["output_dir"])

        reid_cfg = config.get("reid", {})
        device = resolve_device(reid_cfg.get("device") or config.get("device") or "0")

        self.detector = PersonDetector(
            model_name=config.get("model", "yolo11m.pt"),
            conf=config.get("conf", 0.4),
            classes=config.get("classes", [0]),
            device=device,
        )
        self.camera_tracker = CameraTracker(
            detector=self.detector,
            tracker_cfg=config.get("tracker", "bytetrack.yaml"),
            frame_skip=config.get("frame_skip", 2),
            save_crops=True,
        )
        self.embedder = MultiModalEmbedder(
            body_method=reid_cfg.get("body_method", "osnet"),
            face_backend=reid_cfg.get("face_backend", "none"),
            face_weight=reid_cfg.get("face_weight", 0.15),
            device="cuda" if str(device) in ("0", "cuda", "cuda:0") or str(device).isdigit() else device,
        )
        self.topology = CameraTopology(config.get("topology", {}))
        self.profiles = ProfileStore(config.get("profiles_dir", "data/profiles"), self.embedder)
        self.matcher = SeedMatcher(
            topology=self.topology,
            match_threshold=reid_cfg.get("match_threshold", 0.50),
            strong_threshold=reid_cfg.get("strong_match_threshold", 0.65),
            max_time_gap=reid_cfg.get("max_time_gap_seconds", 420),
            face_weight=reid_cfg.get("face_weight", 0.15),
        )
        self.save_track_clips = config.get("save_track_clips", True)
        self.cache = DetectionCache(self.output_dir)

    def validate_topology(self, camera_names: list) -> None:
        self.topology.validate_against_disk(camera_names)

    def run_detection(self, force: bool = False) -> Dict[str, Any]:
        if not force and self.cache.exists():
            loaded = self.cache.load_all()
            if loaded is not None:
                logger.info("Using cached detections (pass --force-detect to re-run YOLO)")
                return loaded

        cameras = list_camera_videos(self.cfg["cameras_root"])
        if not cameras:
            raise RuntimeError(f"No camera videos found under {self.cfg['cameras_root']}")

        self.validate_topology(list(cameras.keys()))
        logger.info("Found %d cameras", len(cameras))

        all_tracks: Dict[str, Dict[int, Track]] = {}
        all_embeddings: Dict[str, Dict[int, dict]] = {}

        for cam_name, videos in cameras.items():
            cam_tracks: Dict[int, Track] = {}
            id_offset = 0
            for video in videos:
                tracks = self.camera_tracker.process_video(video, cam_name)
                for lid, tr in tracks.items():
                    new_id = lid + id_offset
                    tr.track_id = new_id
                    cam_tracks[new_id] = tr
                if tracks:
                    id_offset = max(cam_tracks.keys()) + 1000

            embs = self.embedder.embed_all_tracks(cam_tracks)
            all_tracks[cam_name] = cam_tracks
            all_embeddings[cam_name] = embs
            self.cache.save_camera(cam_name, cam_tracks, embs)

            summary = {
                "camera": cam_name,
                "num_tracks": len(cam_tracks),
                "tracks": [
                    {
                        "local_id": tid,
                        "duration_s": round(tr.duration(), 1),
                        "first_seen": round(tr.start_end()[0], 1),
                        "last_seen": round(tr.start_end()[1], 1),
                        "video": tr.video_path,
                    }
                    for tid, tr in cam_tracks.items()
                ],
            }
            save_json(summary, self.output_dir / "per_camera" / f"{cam_name}.json")

        total = sum(len(t) for t in all_tracks.values())
        self.cache.save_meta(list(cameras.keys()), total)
        return {"tracks": all_tracks, "embeddings": all_embeddings, "cameras": list(cameras.keys())}

    def follow_profile(self, profile_name: str, detection_result: Dict) -> Dict:
        profile = self.profiles.load(profile_name)
        if profile is None:
            raise FileNotFoundError(f"No profile named '{profile_name}'. Run enroll_staff.py first.")
        trail = self.matcher.follow_profile(
            profile, detection_result["tracks"], detection_result["embeddings"]
        )
        return self._finalize_trail(trail, detection_result["tracks"])

    def follow_seed_track(
        self, camera: str, local_id: int, detection_result: Dict, name: str = "seed"
    ) -> Dict:
        tracks = detection_result["tracks"]
        embs = detection_result["embeddings"]
        if camera not in tracks or local_id not in tracks[camera]:
            raise KeyError(f"Track {local_id} not found on camera {camera}")
        tr = tracks[camera][local_id]
        emb = embs.get(camera, {}).get(local_id, {})
        t0, _ = tr.start_end()
        trail = self.matcher.follow_seed(
            emb.get("face"), emb.get("body"), camera, t0,
            tracks, embs, name=name,
        )
        return self._finalize_trail(trail, tracks)

    def _finalize_trail(self, trail, all_tracks: Dict) -> Dict:
        trail_dir = ensure_dir(self.output_dir / "trails" / trail.name)
        appearances = []
        for app in trail.sorted_appearances():
            appearances.append({
                "camera": app.camera,
                "local_id": app.local_id,
                "start_s": round(app.start_s, 1),
                "end_s": round(app.end_s, 1),
                "score": round(app.score, 3),
            })

        report = {
            "name": trail.name,
            "num_appearances": len(appearances),
            "appearances": appearances,
        }

        if self.save_track_clips and appearances:
            refs = [(a["camera"], a["local_id"]) for a in appearances]
            clip_infos = extract_person_clips(
                global_id=0,
                track_refs=refs,
                all_tracks=all_tracks,
                clips_dir=trail_dir / "clips",
            )
            for c, a in zip(clip_infos, report["appearances"]):
                a["clip"] = f"clips/{c['clip']}" if c.get("clip") else None

        save_json(report, trail_dir / "person_trail.json")
        try:
            from scripts.export_report import write_trail_reports
            write_trail_reports(report, trail_dir)
        except Exception:
            pass

        logger.info("Wrote trail → %s", trail_dir)
        return report

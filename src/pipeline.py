from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .cache import DetectionCache
from .clips import extract_person_clips
from .detector import PersonDetector
from .device import resolve_device
from .matcher import SeedMatcher
from .profiles import ProfileStore
from .reid import MultiModalEmbedder
from .timerange import filter_embeddings, filter_tracks_window, window as parse_window
from .topology import CameraTopology
from .tracker import CameraTracker, Track
from .utils import ensure_dir, list_camera_videos, save_json

logger = logging.getLogger(__name__)


class OvernightPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self.output_dir = ensure_dir(config["output_dir"])
        self.tz_name = config.get("timezone") or "America/Chicago"
        # Default source: nvr (pull only the window). local = use dropped clips.
        self.source_mode = (config.get("source_mode") or "nvr").lower()

        reid_cfg = config.get("reid", {})
        device = resolve_device(reid_cfg.get("device") or config.get("device") or "mps")

        self.detector = PersonDetector(
            model_name=config.get("model", "yolo11s.pt"),
            conf=config.get("conf", 0.4),
            classes=config.get("classes", [0]),
            device=device,
        )
        self.camera_tracker = CameraTracker(
            detector=self.detector,
            tracker_cfg=config.get("tracker", "bytetrack.yaml"),
            frame_skip=config.get("frame_skip", 3),
            save_crops=True,
        )
        self.embedder = MultiModalEmbedder(
            body_method=reid_cfg.get("body_method", "osnet"),
            face_backend=reid_cfg.get("face_backend", "none"),
            face_weight=reid_cfg.get("face_weight", 0.15),
            device=device,
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

    def pull_window_from_nvr(
        self,
        start: str,
        end: str,
        cameras: Optional[list] = None,
    ) -> Dict[str, list]:
        """Pull only the requested time window from UniFi/Frigate into cameras_root.
        Returns {folder: [Path, ...]} of written clips.
        """
        from .nvr import export_range, NvrError

        logger.info("NVR pull %s → %s (source_mode=nvr)", start, end)
        try:
            written = export_range(
                self.cfg, start, end,
                cameras=cameras,
                out_root=self.cfg.get("cameras_root") or "data/cameras",
            )
        except NvrError as e:
            raise RuntimeError(f"NVR pull failed: {e}") from e
        total = sum(len(v) for v in written.values())
        logger.info("NVR pulled %d clips across %d cameras", total, len(written))
        return written

    def run_detection(self, force: bool = False, cameras_root: Optional[str] = None) -> Dict[str, Any]:
        if not force and self.cache.exists() and cameras_root is None:
            loaded = self.cache.load_all()
            if loaded is not None:
                logger.info("Using cached detections (pass --force-detect to re-run YOLO)")
                return loaded

        root = cameras_root or self.cfg["cameras_root"]
        cameras = list_camera_videos(root)
        if not cameras:
            raise RuntimeError(f"No camera videos found under {root}")

        self.validate_topology(list(cameras.keys()))
        logger.info("Found %d cameras under %s", len(cameras), root)

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

    def apply_window(
        self,
        detection: Dict[str, Any],
        start: Optional[str] = None,
        end: Optional[str] = None,
        start_s: Optional[float] = None,
        end_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        t0, t1 = parse_window(start, end, self.tz_name)
        tracks = filter_tracks_window(
            detection["tracks"], t0, t1,
            tz_name=self.tz_name, start_s=start_s, end_s=end_s,
        )
        embs = filter_embeddings(detection["embeddings"], tracks)
        return {
            "tracks": tracks,
            "embeddings": embs,
            "cameras": list(tracks.keys()),
            "window": {
                "start": t0.isoformat() if t0 else None,
                "end": t1.isoformat() if t1 else None,
                "start_s": start_s,
                "end_s": end_s,
            },
        }

    def search_person(
        self,
        profile_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        start_s: Optional[float] = None,
        end_s: Optional[float] = None,
        source: Optional[str] = None,
        force_detect: bool = False,
        cameras: Optional[list] = None,
    ) -> Dict:
        """High-level search: NVR pull (default) or local folders, then match profile."""
        mode = (source or self.source_mode or "nvr").lower()
        if mode == "nvr":
            if not start or not end:
                raise ValueError("NVR mode needs --start and --end (e.g. 20:00 03:00)")
            # Pull only this window — not the whole night archive
            self.pull_window_from_nvr(start, end, cameras=cameras)
            detection = self.run_detection(force=True)  # process just-pulled clips
            detection = self.apply_window(detection, start=start, end=end, start_s=start_s, end_s=end_s)
        else:
            detection = self.run_detection(force=force_detect)
            detection = self.apply_window(detection, start=start, end=end, start_s=start_s, end_s=end_s)

        report = self.follow_profile(profile_name, detection)
        report["window"] = detection.get("window") or {"start": start, "end": end}
        report["source_mode"] = mode
        return report

    def follow_profile(self, profile_name: str, detection_result: Dict) -> Dict:
        profile = self.profiles.load(profile_name)
        if profile is None:
            raise FileNotFoundError(f"No profile named '{profile_name}'. Run tag_person.py or enroll_staff.py first.")
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

    def follow_profile_crop(
        self, name: str, detection_result: Dict, face, body
    ) -> Dict:
        tracks = detection_result["tracks"]
        embs = detection_result["embeddings"]
        best = None
        best_score = -1.0
        for cam, trs in tracks.items():
            for lid, tr in trs.items():
                emb = embs.get(cam, {}).get(lid, {})
                score = self.matcher._score(face, body, emb.get("face"), emb.get("body"))
                if score > best_score:
                    best_score = score
                    best = (cam, tr.start_end()[0])
        if best is None:
            return {"name": name, "num_appearances": 0, "appearances": []}
        trail = self.matcher.follow_seed(
            face, body, best[0], best[1], tracks, embs, name=name,
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

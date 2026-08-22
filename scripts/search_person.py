#!/usr/bin/env python3
"""Tag or load a profile, then find every appearance in a time window.

Default source is NVR: pulls only the requested window from UniFi/Frigate,
then searches. Use --source local for pre-dropped clips.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import OvernightPipeline
from src.tag import save_tag_session
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find one person across cameras in a time period"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--profile", help="Enrolled staff name")
    parser.add_argument("--video", help="Clip to tag from (with --at --pick)")
    parser.add_argument("--at", help="Timestamp in that clip")
    parser.add_argument("--pick", type=int, default=0, help="Person index in the tagged frame")
    parser.add_argument("--name", default="target", help="Trail name if not using --profile")
    parser.add_argument("--seed-camera")
    parser.add_argument("--seed-track", type=int)
    parser.add_argument("--start", help="Window start: 20:00 or 2026-08-21 20:00")
    parser.add_argument("--end", help="Window end: 03:00 (wraps overnight)")
    parser.add_argument("--start-s", type=float, help="Relative seconds into clips")
    parser.add_argument("--end-s", type=float)
    parser.add_argument(
        "--source",
        choices=["nvr", "local"],
        default=None,
        help="nvr = pull only this window from Protect/Frigate (default). local = use dropped clips",
    )
    parser.add_argument("--force-detect", action="store_true")
    args = parser.parse_args()

    tagged = bool(args.video and args.at is not None)
    seeded = bool(args.seed_camera and args.seed_track is not None)
    if not args.profile and not tagged and not seeded:
        parser.error("Provide --profile, or --video --at, or --seed-camera --seed-track")

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))
    pipeline = OvernightPipeline(cfg)
    source = args.source or cfg.get("source_mode") or "nvr"

    if tagged and not args.profile:
        session = save_tag_session(
            args.video, args.at,
            Path(cfg.get("output_dir", "data/output")) / "tags" / "search",
            model_name=cfg.get("model", "yolo11n.pt"),
        )
        chosen = [p for p in session["people"] if p["index"] == args.pick]
        if not chosen:
            raise SystemExit(f"No person #{args.pick} in that frame")
        store = pipeline.profiles
        store.enroll_from_crops(
            name=args.name,
            crops=[chosen[0]["crop"]],
            role="tagged",
            notes=f"search tag @ {session['at_s']:.1f}s",
        )
        args.profile = args.name
        print(f"Tagged person #{args.pick} as '{args.name}'")

    if args.profile:
        print(f"Searching '{args.profile}' via source={source} ...")
        report = pipeline.search_person(
            profile_name=args.profile,
            start=args.start,
            end=args.end,
            start_s=args.start_s,
            end_s=args.end_s,
            source=source,
            force_detect=args.force_detect,
        )
        label = args.profile
    else:
        print("Loading detections (cache if available)...")
        detection = pipeline.run_detection(force=args.force_detect)
        detection = pipeline.apply_window(
            detection, start=args.start, end=args.end,
            start_s=args.start_s, end_s=args.end_s,
        )
        report = pipeline.follow_seed_track(
            args.seed_camera, args.seed_track, detection, name=args.name
        )
        label = args.name

    print("\n===== Search complete =====")
    print(f"Person      : {label}")
    print(f"Source      : {report.get('source_mode', source)}")
    print(f"Appearances : {report['num_appearances']}")
    if report.get("window", {}).get("start"):
        print(f"Window      : {report['window']['start']} → {report['window']['end']}")
    print(f"Trail       : {cfg['output_dir']}/trails/{label}/report.html")
    for a in report.get("appearances", [])[:20]:
        print(f"  {a['camera']:16s}  {a['start_s']:7.1f}s → {a['end_s']:7.1f}s  score={a['score']:.2f}")
    if report["num_appearances"] > 20:
        print(f"  ... and {report['num_appearances'] - 20} more")


if __name__ == "__main__":
    main()

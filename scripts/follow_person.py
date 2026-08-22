#!/usr/bin/env python3
"""Seed → Follow: track one individual across the whole night."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import OvernightPipeline
from src.utils import load_config, setup_logging, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Follow one person across all cameras")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--profile", help="Name of enrolled staff profile")
    parser.add_argument("--seed-camera", help="Camera of the seed track")
    parser.add_argument("--seed-track", type=int, help="Local track ID of the seed")
    parser.add_argument("--name", default="target", help="Name to give this trail when using seed-track")
    args = parser.parse_args()

    if not args.profile and not (args.seed_camera and args.seed_track is not None):
        parser.error("Provide either --profile or both --seed-camera and --seed-track")

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    pipeline = OvernightPipeline(cfg)

    print("Running full detection + tracking pass (this can take a while)...")
    detection = pipeline.run_detection()

    if args.profile:
        report = pipeline.follow_profile(args.profile, detection)
        label = args.profile
    else:
        report = pipeline.follow_seed_track(
            args.seed_camera, args.seed_track, detection, name=args.name
        )
        label = args.name

    print("\n===== Person Trail complete =====")
    print(f"Person          : {label}")
    print(f"Appearances     : {report['num_appearances']}")
    print(f"Trail written to: {cfg['output_dir']}/trails/{label}/")
    for a in report.get("appearances", [])[:12]:
        print(f"  {a['camera']:15s}  {a['start_s']:7.1f}s → {a['end_s']:7.1f}s  score={a['score']:.2f}")
    if report['num_appearances'] > 12:
        print(f"  ... and {report['num_appearances'] - 12} more")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run full detection + tracking across all cameras and cache results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import OvernightPipeline
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--force", action="store_true", help="Re-run even if cache exists")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    pipeline = OvernightPipeline(cfg)
    result = pipeline.run_detection(force=args.force)

    total = sum(len(t) for t in result["tracks"].values())
    print("\n===== Detection pass complete =====")
    print(f"Cameras : {len(result['cameras'])}")
    print(f"Tracks  : {total}")
    print(f"Cache   : {cfg['output_dir']}/cache/")
    print("Next: python scripts/follow_person.py --profile <name>")


if __name__ == "__main__":
    main()

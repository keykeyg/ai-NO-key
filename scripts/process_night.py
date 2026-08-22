#!/usr/bin/env python3
"""Overnight multi-camera person tracking job."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make src importable when running as script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline import OvernightPipeline
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="AI No Key – process a night of multi-camera footage")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    pipeline = OvernightPipeline(cfg)
    report = pipeline.run()

    print("\n===== Night processing complete =====")
    print(f"Cameras processed : {report['num_cameras']}")
    print(f"Unique people     : {report['num_global_people']}")
    print(f"Report written to : {cfg['output_dir']}/global_report.json")


if __name__ == "__main__":
    main()

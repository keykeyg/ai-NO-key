#!/usr/bin/env python3
"""Pull a time window of footage from UniFi Protect or Frigate into data/cameras/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.nvr import NvrError, export_range
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Export NVR clips for a time period")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--start", required=True, help="e.g. 21:00 or 2026-08-21 21:00")
    parser.add_argument("--end", required=True, help="e.g. 03:00 (overnight wrap ok)")
    parser.add_argument("--cameras", nargs="*", help="Camera names (default: all mapped)")
    parser.add_argument("--out", default=None, help="Override cameras_root")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    try:
        written = export_range(
            cfg, args.start, args.end,
            cameras=args.cameras, out_root=args.out,
        )
    except NvrError as e:
        raise SystemExit(f"NVR pull failed: {e}")

    if not written:
        print("No clips exported. Check nvr.host / credentials / camera names.")
        return

    print("\n===== NVR export complete =====")
    total = 0
    for folder, files in written.items():
        print(f"  {folder}: {len(files)} clips")
        total += len(files)
    print(f"Total: {total} files under {args.out or cfg.get('cameras_root')}")
    print("Next:")
    print("  python scripts/process_night.py --config config.yaml --force")
    print("  python scripts/search_person.py --profile Marcus --start " + args.start + " --end " + args.end)


if __name__ == "__main__":
    main()

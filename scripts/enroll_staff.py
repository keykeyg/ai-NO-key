#!/usr/bin/env python3
"""Enroll a staff member with photos, or from a tagged frame crop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.device import resolve_device
from src.profiles import ProfileStore
from src.reid import MultiModalEmbedder
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Enroll staff for Seed → Follow tracking")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--images", nargs="+", help="One or more image paths")
    args = parser.parse_args()

    if not args.images:
        parser.error("Provide --images. To tag from a video frame use scripts/tag_person.py")

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    reid_cfg = cfg.get("reid", {})
    embedder = MultiModalEmbedder(
        body_method=reid_cfg.get("body_method", "osnet"),
        face_backend=reid_cfg.get("face_backend", "none"),
        face_weight=reid_cfg.get("face_weight", 0.15),
        device=resolve_device(reid_cfg.get("device") or cfg.get("device") or "mps"),
    )
    store = ProfileStore(cfg.get("profiles_dir", "data/profiles"), embedder)

    profile = store.enroll_from_images(
        name=args.name,
        image_paths=args.images,
        role=args.role,
        notes=args.notes,
    )
    print(f"Enrolled {profile.name} ({profile.role})")
    print(f"  Face embeddings : {len(profile.face_embeddings)}")
    print(f"  Body embeddings : {len(profile.body_embeddings)}")
    print(f"  Profile saved to: {store.profile_path(profile.name)}")


if __name__ == "__main__":
    main()

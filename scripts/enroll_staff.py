#!/usr/bin/env python3
"""Enroll a staff member with one or more reference photos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.profiles import ProfileStore
from src.reid import MultiModalEmbedder
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Enroll staff for Seed → Follow tracking")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--name", required=True, help="Staff name (e.g. Marcus)")
    parser.add_argument("--role", default="", help="manager / bartender / hookah / etc.")
    parser.add_argument("--notes", default="")
    parser.add_argument("--images", nargs="+", required=True, help="One or more image paths")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    embedder = MultiModalEmbedder(
        body_method=cfg.get("reid", {}).get("body_method", "enhanced"),
        face_enabled=cfg.get("reid", {}).get("face_enabled", True),
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

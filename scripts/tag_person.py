#!/usr/bin/env python3
"""Tag a person in a frame, then optionally enroll them."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.device import resolve_device
from src.profiles import ProfileStore
from src.reid import MultiModalEmbedder
from src.tag import save_tag_session
from src.utils import load_config, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pause a clip, number every person, enroll the one you pick"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--video", required=True, help="Path to a camera clip")
    parser.add_argument("--at", required=True, help="Timestamp: seconds or HH:MM:SS into the clip")
    parser.add_argument("--pick", type=int, default=None, help="Person index to enroll (# on overview)")
    parser.add_argument("--name", help="Profile name when using --pick")
    parser.add_argument("--role", default="")
    parser.add_argument("--out", default=None, help="Folder for overview + crops")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("log_level", "INFO"))

    video = Path(args.video)
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")

    out = Path(args.out) if args.out else Path(cfg.get("output_dir", "data/output")) / "tags" / video.stem[:40]
    session = save_tag_session(video, args.at, out, model_name=cfg.get("model", "yolo11n.pt"))

    print(f"\nFrame at {session['at_s']:.1f}s — {session['num_people']} people")
    print(f"Overview: {session['overview']}")
    for c in session["crops"]:
        print(f"  #{c['index']}  conf={c['conf']:.2f}  {c['path']}")

    if session["num_people"] == 0:
        raise SystemExit("No people in that frame. Try a different --at timestamp.")

    if args.pick is None:
        print("\nOpen the overview, pick a number, then re-run with:")
        print(f"  python scripts/tag_person.py --video \"{video}\" --at {args.at} --pick 0 --name Marcus")
        return

    if not args.name:
        raise SystemExit("--name is required when using --pick")

    chosen = [p for p in session["people"] if p["index"] == args.pick]
    if not chosen:
        raise SystemExit(f"No person #{args.pick}. Valid: 0..{session['num_people']-1}")

    reid_cfg = cfg.get("reid", {})
    embedder = MultiModalEmbedder(
        body_method=reid_cfg.get("body_method", "osnet"),
        face_backend=reid_cfg.get("face_backend", "none"),
        face_weight=reid_cfg.get("face_weight", 0.15),
        device=resolve_device(reid_cfg.get("device") or cfg.get("device") or "mps"),
    )
    store = ProfileStore(cfg.get("profiles_dir", "data/profiles"), embedder)
    crop_path = next(c["path"] for c in session["crops"] if c["index"] == args.pick)
    profile = store.enroll_from_crops(
        name=args.name,
        crops=[chosen[0]["crop"]],
        saved_paths=[crop_path],
        role=args.role,
        notes=f"tagged from {video.name} @ {session['at_s']:.1f}s",
    )
    print(f"\nTagged + enrolled {profile.name}")
    print(f"  Body embeddings : {len(profile.body_embeddings)}")
    print(f"  Profile         : {store.profile_path(profile.name)}")
    print(f"\nSearch them in a time window:")
    print(f"  python scripts/search_person.py --profile {profile.name} --start 21:00 --end 03:00")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_camera_videos(cameras_root: str | Path) -> Dict[str, List[Path]]:
    """Return {camera_name: [video_paths]} from a folder structure."""
    root = Path(cameras_root)
    if not root.exists():
        raise FileNotFoundError(f"cameras_root not found: {root}")

    cameras: Dict[str, List[Path]] = {}
    for cam_dir in sorted(root.iterdir()):
        if not cam_dir.is_dir():
            continue
        videos = sorted(
            list(cam_dir.glob("*.mp4"))
            + list(cam_dir.glob("*.mkv"))
            + list(cam_dir.glob("*.avi"))
            + list(cam_dir.glob("*.mov"))
        )
        if videos:
            cameras[cam_dir.name] = videos
    return cameras


def save_json(data: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

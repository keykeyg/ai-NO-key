from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from .reid import MultiModalEmbedder
from .utils import ensure_dir, save_json

logger = logging.getLogger(__name__)


@dataclass
class StaffProfile:
    name: str
    role: str = ""
    notes: str = ""
    image_paths: List[str] = field(default_factory=list)
    face_embeddings: List[List[float]] = field(default_factory=list)
    body_embeddings: List[List[float]] = field(default_factory=list)

    def mean_face(self) -> Optional[np.ndarray]:
        if not self.face_embeddings:
            return None
        arr = np.array(self.face_embeddings, dtype=np.float32)
        v = arr.mean(axis=0)
        return v / (np.linalg.norm(v) + 1e-8)

    def mean_body(self) -> Optional[np.ndarray]:
        if not self.body_embeddings:
            return None
        arr = np.array(self.body_embeddings, dtype=np.float32)
        v = arr.mean(axis=0)
        return v / (np.linalg.norm(v) + 1e-8)


def _largest_person_crop(img: np.ndarray, model_name: str = "yolo11n.pt") -> Optional[np.ndarray]:
    """Run a quick person detector on an enrollment photo and return the largest person crop."""
    try:
        from ultralytics import YOLO
        model = YOLO(model_name)
        results = model.predict(img, classes=[0], conf=0.35, verbose=False)
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return None
        boxes = results[0].boxes.xyxy.cpu().numpy()
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        i = int(areas.argmax())
        x1, y1, x2, y2 = map(int, boxes[i])
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return img[y1:y2, x1:x2].copy()
    except Exception as e:
        logger.warning("Enrollment person detect failed: %s — using full image", e)
        return None


class ProfileStore:
    def __init__(self, profiles_dir: str | Path, embedder: MultiModalEmbedder):
        self.root = ensure_dir(profiles_dir)
        self.embedder = embedder

    def profile_path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self.root / f"{safe}.json"

    def save(self, profile: StaffProfile) -> Path:
        path = self.profile_path(profile.name)
        save_json(asdict(profile), path)
        logger.info("Saved profile %s → %s", profile.name, path)
        return path

    def load(self, name: str) -> Optional[StaffProfile]:
        path = self.profile_path(name)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StaffProfile(**data)

    def list_profiles(self) -> List[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def enroll_from_images(
        self,
        name: str,
        image_paths: List[str | Path],
        role: str = "",
        notes: str = "",
        detect_person: bool = True,
    ) -> StaffProfile:
        face_embs = []
        body_embs = []
        kept_paths = []

        for p in image_paths:
            p = Path(p)
            if not p.exists():
                logger.warning("Missing image: %s", p)
                continue
            img = cv2.imread(str(p))
            if img is None:
                continue

            crop = img
            if detect_person:
                person = _largest_person_crop(img)
                if person is not None:
                    crop = person
                else:
                    logger.warning("No person detected in %s — using full image", p.name)

            face_e, body_e = self.embedder.embed_image(crop)
            if body_e is not None:
                body_embs.append(body_e.tolist())
                kept_paths.append(str(p))
            if face_e is not None:
                face_embs.append(face_e.tolist())

        if not body_embs and not face_embs:
            raise RuntimeError(f"Could not extract any embeddings for {name}")

        profile = StaffProfile(
            name=name,
            role=role,
            notes=notes,
            image_paths=kept_paths,
            face_embeddings=face_embs,
            body_embeddings=body_embs,
        )
        self.save(profile)
        return profile

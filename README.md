# AI No Key

**Local overnight multi-camera person tracking built for busy bars.**

Track a specific individual (manager, bartender, hookah staff) from a seed appearance at the beginning of the shift all the way through the night across 30+ cameras.

Designed as a practical, stronger alternative to UniFi Protect AI Key for environments where faces are often not visible and detection queues would overflow.

---

## Core Goal

**Seed → Follow**

1. Enroll key staff (or pick a clear early appearance).
2. Process the entire previous night’s footage offline on an RTX 3090.
3. Receive a continuous **Person Trail**: every camera that person appeared on, in time order, with short review clips.

This works even when the person is mostly seen from behind, in dark areas, or in crowded sections of the bar.

---

## Why this exists

UniFi AI Key is excellent at enriching detections and letting you name faces, but it has hard limits in a real bar:

- Detection queue (~200) and hourly caps mean many events are dropped on busy nights.
- Heavy reliance on clear faces.
- No strong continuous “follow this one person all night” mode.
- No use of staff movement patterns between cameras.

AI No Key is built specifically to solve those problems with offline full-pass processing, multi-modal identity (face + body), and camera topology priors.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design rationale and research notes.

---

## Features

- Staff profile enrollment (multiple reference photos per person)
- Multi-modal identity (face when available + body/clothing ReID)
- Seed → Follow mode for a single individual
- Camera topology / transition priors
- Overnight batch processing of many cameras on one GPU
- Person Trail report + ordered short clips
- HTML + Markdown output for quick morning review

---

## Quick Start

```bash
git clone https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
# Edit paths, camera list, and topology for your bars
```

### 1. Enroll staff (do this once)

```bash
python scripts/enroll_staff.py --name "Marcus" --role manager --images path/to/photos/
```

### 2. Put the night’s videos in place

```
data/cameras/
  bar_main/2026-08-21.mp4
  hookah/2026-08-21.mp4
  kitchen/2026-08-21.mp4
  ...
```

### 3. Run overnight job (full detection + tracking)

```bash
python scripts/process_night.py --config config.yaml
```

### 4. Follow a specific person

```bash
# Using an enrolled profile
python scripts/follow_person.py --config config.yaml --profile Marcus

# Or seed from a specific local track that appeared early
python scripts/follow_person.py --config config.yaml --seed-camera bar_main --seed-track 12
```

### 5. Review

Open `data/output/trails/Marcus/report.html` (or the equivalent for the seed you chose).

---

## Project Layout

```
ai-NO-key/
├── ARCHITECTURE.md          # Full design + UniFi comparison
├── README.md
├── config.example.yaml
├── requirements.txt
├── scripts/
│   ├── enroll_staff.py      # Create staff profiles
│   ├── process_night.py     # Detect + track all cameras
│   ├── follow_person.py     # Seed → Follow mode
│   └── export_report.py
├── src/
│   ├── detector.py
│   ├── tracker.py
│   ├── reid.py              # Multi-modal embeddings
│   ├── profiles.py          # Staff gallery
│   ├── topology.py          # Camera transition graph
│   ├── matcher.py           # Seed matching + global association
│   ├── clips.py
│   ├── pipeline.py
│   └── utils.py
└── data/                    # videos, profiles, output (gitignored)
```

---

## Hardware

- RTX 3090 (24 GB) or better recommended
- 64 GB+ system RAM for large nights
- Fast storage for the night’s video files

Processing is sequential/grouped per camera so VRAM stays manageable.

---

## Status

This is a working foundation focused on the exact goal above.  
The biggest future accuracy upgrade is swapping the body embedding for a real OSNet / Torchreid model (the interfaces are already in place).

---

## License

Private.

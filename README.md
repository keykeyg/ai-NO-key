# AI No Key

Local overnight multi-camera person tracking and re-identification pipeline.

Built as a practical DIY alternative to UniFi Protect AI Key for ~30 cameras.
Designed for batch processing of the previous night's footage on a single RTX 3090 (or better).

## What it does

1. Processes video files (or folders of clips) from many cameras
2. Detects people with YOLO
3. Tracks them per-camera with ByteTrack / BoT-SORT
4. Extracts appearance embeddings (OSNet-style ReID)
5. Matches the same person across cameras into global IDs
6. Outputs a clean report of movement timelines + optional annotated clips

Not real-time. Optimized for overnight batch jobs that finish in a few hours.

## Hardware target

- RTX 3090 (24 GB) or similar
- 64 GB+ system RAM recommended for 30 cameras
- Fast storage for the night's video files

## Quick start

```bash
# Clone
git clone https://github.com/keykeyg/ai-no-key.git
cd ai-no-key

# Create environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate

# Install
pip install -r requirements.txt

# Put your night's videos here (one folder per camera)
# data/cameras/cam01/night.mp4
# data/cameras/cam02/night.mp4
# ...

# Edit config
cp config.example.yaml config.yaml
# then set your camera paths and settings

# Run overnight job
python scripts/process_night.py --config config.yaml
```

## Project layout

```
ai-no-key/
├── config.example.yaml
├── requirements.txt
├── scripts/
│   ├── process_night.py      # main overnight runner
│   └── export_report.py      # turn results into readable report
├── src/
│   ├── detector.py           # YOLO wrapper
│   ├── tracker.py            # per-camera tracking
│   ├── reid.py               # appearance embeddings
│   ├── matcher.py            # cross-camera global ID assignment
│   ├── pipeline.py           # full overnight pipeline
│   └── utils.py
└── data/                     # your videos + outputs (gitignored)
```

## Design notes

- **Batch, not live** — we process completed recordings. This lets us use larger models and better ReID.
- **One GPU** — cameras are processed sequentially or in small groups so VRAM stays under control.
- **ReID is the hard part** — single-camera tracking is easy; matching the same person across non-overlapping cameras is where most systems fail. We use appearance embeddings + time windows.
- **Output is actionable** — JSON + simple timeline reports so you can actually use the results the next morning.

## Status

Early but usable. Core detection + tracking + basic cross-camera matching works. Next priorities: better gallery management, UniFi Protect export helpers, and a simple web report view.

## License

Private for now.

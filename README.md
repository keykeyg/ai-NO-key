# AI No Key

Local overnight multi-camera person tracking and re-identification pipeline.

Built as a practical DIY alternative to UniFi Protect AI Key for ~30 cameras.
Designed for batch processing of the previous night's footage on a single RTX 3090 (or better).

## What it does

1. Processes video files from many cameras
2. Detects people with YOLO
3. Tracks them per-camera with ByteTrack / BoT-SORT
4. Extracts appearance embeddings
5. Matches the same person across cameras into global IDs
6. Cuts short review clips for each person
7. Writes a timeline report + clickable HTML viewer

Not real-time. Optimized for overnight batch jobs that finish in a few hours.

## Hardware target

- RTX 3090 (24 GB) or similar
- 64 GB+ system RAM recommended for 30 cameras
- Fast storage for the night's video files

## Quick start

```bash
git clone https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate

pip install -r requirements.txt

# Put your night's videos here (one folder per camera)
# data/cameras/cam01/night.mp4
# data/cameras/cam02/night.mp4
# ...

cp config.example.yaml config.yaml
# edit paths if needed

python scripts/process_night.py --config config.yaml
python scripts/export_report.py
```

Then open `data/output/report.html` in a browser. You can click the clip links to jump straight to each camera appearance of a person.

## Project layout

```
ai-NO-key/
├── config.example.yaml
├── requirements.txt
├── scripts/
│   ├── process_night.py      # main overnight runner
│   └── export_report.py      # markdown + HTML report
├── src/
│   ├── detector.py
│   ├── tracker.py
│   ├── reid.py
│   ├── matcher.py
│   ├── clips.py              # track / person clip extraction
│   ├── pipeline.py
│   └── utils.py
└── data/                     # your videos + outputs (gitignored)
```

## Outputs

After a run you get:

- `data/output/global_report.json` — full structured results
- `data/output/per_camera/*.json` — per-camera track lists
- `data/output/clips/person_XXXX/*.mp4` — short review clips per person
- `data/output/night_summary.md` — readable timeline
- `data/output/report.html` — clickable viewer

## Design notes

- **Batch, not live** — process completed recordings so we can use larger models and better ReID.
- **One GPU** — cameras are processed sequentially so VRAM stays under control on a 3090.
- **ReID is the hard part** — single-camera tracking is easy; matching the same person across non-overlapping cameras is where most systems fail.
- **Clips are the point** — the goal is to make the next morning review fast: open the HTML, click a person, watch every camera they appeared on.

## Status

Usable core. Detection + tracking + basic cross-camera matching + clip extraction + HTML report are in.

Next priorities:
- Full OSNet / Torchreid embeddings
- UniFi Protect / Frigate helpers to pull the night's clips automatically
- Stronger gallery management and temporal constraints

## License

Private for now.

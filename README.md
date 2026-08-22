# AI No Key

**Track one staff member across 30+ bar cameras for an entire night.**

Seed → Follow pipeline: enroll a manager/bartender/hookah lead (or pick an early appearance), process the night offline on a 3090, get a continuous Person Trail with ordered clips.

Built as a stronger alternative to UniFi Protect AI Key for crowded, dark bar conditions.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design + UniFi research notes.

---

## Install

```bash
git clone https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# OSNet (strongly recommended)
bash scripts/setup_reid.sh
# or: pip install git+https://github.com/KaiyangZhou/deep-person-reid.git

cp config.example.yaml config.yaml
# Edit camera names + topology to match your bars
```

---

## Workflow

```bash
# 1. Enroll staff (person-cropped automatically)
python scripts/enroll_staff.py --name Marcus --role manager --images m1.jpg m2.jpg m3.jpg

# 2. Full night detection (cached)
python scripts/process_night.py --config config.yaml

# 3. Follow that person (uses cache — fast)
python scripts/follow_person.py --profile Marcus

# 4. Open the trail
# data/output/trails/Marcus/report.html
```

Seed from a live early track instead of a profile:

```bash
python scripts/follow_person.py --seed-camera bar_main --seed-track 12 --name Marcus
```

Re-run YOLO only when needed:

```bash
python scripts/follow_person.py --profile Marcus --force-detect
```

---

## What is implemented

| Piece | Status |
|-------|--------|
| Staff enrollment + person crop | Done |
| YOLO + ByteTrack per camera | Done |
| OSNet body ReID (torchreid) | Done (falls back if missing) |
| InsightFace face path | Ready (`face_backend: insightface`) |
| Detection cache | Done |
| Seed → Follow matcher + gap penalty | Done |
| Camera topology validation | Done |
| Person Trail + clips + HTML | Done |

---

## Config tips for a busy bar

- Set `topology.cameras` and `transitions` to your real layout — this is a major accuracy lever.
- Keep `face_backend: none` until InsightFace is installed and tested.
- `body_method: osnet` is the default. If torchreid is not installed it automatically uses the hand-crafted fallback.

---

## License

Private.

# AI No Key

**Tag a person. Search a time window. Get every appearance across 30+ bar cameras.**

Seed → Follow for managers / bartenders / hookah staff. Overnight batch, not real-time.

---

## Branches (use the right one)

| Branch | Machine | Defaults |
|--------|---------|----------|
| **[`windows`](https://github.com/keykeyg/ai-NO-key/tree/windows)** | RTX 3090 / NVIDIA CUDA | `yolo11m`, `frame_skip: 2`, `device: cuda` |
| **[`mac`](https://github.com/keykeyg/ai-NO-key/tree/mac)** | M-series MacBook (32GB+) | `yolo11s`, `frame_skip: 3`, `device: mps` |
| `main` | Shared base | CUDA-first, MPS fallback |

### Clone

```bash
# 3090 desktop
git clone -b windows https://github.com/keykeyg/ai-NO-key.git

# M-series Mac
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
```

---

## The loop

```bash
# 1) Tag a person in a frame (numbered crops)
python scripts/tag_person.py --video "data/cameras/test_cam/yourclip.mp4" --at 5

# 2) Enroll the one you picked
python scripts/tag_person.py \
  --video "data/cameras/test_cam/yourclip.mp4" \
  --at 5 --pick 0 --name Marcus --role hookah

# 3) Find them in a time period (uses detection cache)
python scripts/search_person.py --profile Marcus --start 21:00 --end 03:00
```

Open `data/output/trails/Marcus/report.html`.

`--end 03:00` after `--start 21:00` wraps overnight. Protect filenames (`...-Aug 21, 11:33 PM - Aug 21, 11:35 PM.mp4`) map to wall clock.

---

## Pull last night from UniFi Protect

```bash
export UNIFI_HOST=192.168.1.1
export UNIFI_USERNAME=admin
export UNIFI_PASSWORD='...'

python scripts/pull_nvr.py --start "2026-08-21 21:00" --end "2026-08-22 03:00"
python scripts/process_night.py --config config.yaml --force
python scripts/search_person.py --profile Marcus --start 21:00 --end 03:00
```

Frigate: set `nvr.type: frigate` and `nvr.port: 5000`.

---

## Setup

```bash
cd ai-NO-key
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
bash scripts/setup_reid.sh   # OSNet; optional on Mac if it fails

cp config.example.yaml config.yaml
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for design + UniFi AI Key comparison.

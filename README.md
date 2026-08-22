# AI No Key

**Track one staff member across 30+ bar cameras for an entire night.**

Seed → Follow pipeline for managers / bartenders / hookah staff. Offline batch on GPU. Continuous Person Trail with ordered clips.

---

## Branches (use the right one)

| Branch | Machine | Defaults |
|--------|---------|----------|
| **[`windows`](https://github.com/keykeyg/ai-NO-key/tree/windows)** | RTX 3090 / NVIDIA CUDA | `yolo11m`, `frame_skip: 2`, `device: cuda` |
| **[`mac`](https://github.com/keykeyg/ai-NO-key/tree/mac)** | M-series MacBook (32GB+) | `yolo11s`, `frame_skip: 3`, `device: mps` |
| `main` | Shared base | Same core logic |

### Clone

```bash
# Your 3090 desktop
git clone -b windows https://github.com/keykeyg/ai-NO-key.git

# Brother's M5 MacBook Pro Max 32GB
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
```

---

## Quick workflow (both platforms)

```bash
cd ai-NO-key
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
bash scripts/setup_reid.sh   # OSNet; optional on Mac if it fails

cp config.example.yaml config.yaml
# Edit topology camera names

python scripts/enroll_staff.py --name Marcus --role manager --images m1.jpg m2.jpg
python scripts/process_night.py --config config.yaml
python scripts/follow_person.py --profile Marcus
```

Open `data/output/trails/Marcus/report.html`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design + UniFi comparison.

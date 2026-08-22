# AI No Key — **mac** branch

Apple Silicon optimized build (M-series MacBook Pro, 32GB+ recommended).

Uses **MPS** for YOLO, lighter defaults (`yolo11s`, `frame_skip: 3`), and auto device resolution so CUDA settings are not required.

---

## Setup (Mac)

```bash
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# OSNet (recommended; may fall back to CPU/enhanced on Mac)
bash scripts/setup_reid.sh

cp config.example.yaml config.yaml
# Edit topology camera names to match your folders
```

Verify MPS:

```bash
python -c "import torch; print('mps', torch.backends.mps.is_available())"
```

---

## Workflow

```bash
python scripts/enroll_staff.py --name Marcus --role manager --images m1.jpg m2.jpg
python scripts/process_night.py --config config.yaml
python scripts/follow_person.py --profile Marcus
```

Open `data/output/trails/Marcus/report.html`.

---

## Mac notes

| Setting | Mac default | Why |
|---------|-------------|-----|
| `model` | `yolo11s.pt` | Faster on MPS than `yolo11m` |
| `frame_skip` | `3` | Overnight still accurate, less work |
| `device` | `mps` | Apple GPU |
| OSNet | try MPS/CPU | torchreid is CUDA-first; auto-fallback exists |

If a night is too slow, raise `frame_skip` to `4` or use `yolo11n.pt`.

32GB unified memory is enough because cameras are processed **one at a time**.

---

## Branches

| Branch | For |
|--------|-----|
| `mac` | Apple Silicon (this branch) |
| `windows` | NVIDIA CUDA (3090 etc.) |
| `main` | Shared base |

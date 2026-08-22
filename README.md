# AI No Key — **windows** branch

NVIDIA CUDA optimized build (RTX 3090 and similar).

Uses **CUDA** for YOLO + OSNet, `yolo11m`, and `frame_skip: 2` for higher accuracy on a full night of ~30 cameras.

---

## Setup (Windows)

```powershell
git clone -b windows https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# OSNet
pip install gdown
pip install git+https://github.com/KaiyangZhou/deep-person-reid.git

copy config.example.yaml config.yaml
# Edit topology camera names to match your folders
```

Verify CUDA:

```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no gpu')"
```

---

## Workflow

```powershell
python scripts/enroll_staff.py --name Marcus --role manager --images m1.jpg m2.jpg
python scripts/process_night.py --config config.yaml
python scripts/follow_person.py --profile Marcus
```

Open `data\output\trails\Marcus\report.html`.

---

## Windows / 3090 notes

| Setting | Default | Why |
|---------|---------|-----|
| `model` | `yolo11m.pt` | Good accuracy on 24GB VRAM |
| `frame_skip` | `2` | Dense sampling for crowded bar |
| `device` | `0` / `cuda` | First NVIDIA GPU |
| OSNet | CUDA | Primary body ReID path |

Optional: install InsightFace and set `face_backend: insightface`.

---

## Branches

| Branch | For |
|--------|-----|
| `windows` | NVIDIA CUDA (this branch) |
| `mac` | Apple Silicon MPS |
| `main` | Shared base |

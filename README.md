# AI No Key — **windows** branch

Tag someone. Search a time window. Get every appearance across cameras.

NVIDIA CUDA (RTX 3090). `yolo11m`, `frame_skip: 2`.

---

## The loop you wanted

```powershell
git pull
# still on branch windows

# 1) Tag a person in a frame (numbered crops)
python scripts/tag_person.py --video "data\cameras\test_cam\yourclip.mp4" --at 5

# 2) Enroll the one you picked
python scripts/tag_person.py --video "data\cameras\test_cam\yourclip.mp4" --at 5 --pick 0 --name Marcus --role hookah

# 3) Find them in a time period (uses detection cache)
python scripts/search_person.py --profile Marcus --start 21:00 --end 03:00
```

Open `data\output\trails\Marcus\report.html`.

`--end 03:00` after `--start 21:00` wraps overnight.

---

## Pull last night from UniFi Protect

Edit `config.yaml` → `nvr.host` + camera name map. Credentials via env is safer:

```powershell
$env:UNIFI_HOST="192.168.1.1"
$env:UNIFI_USERNAME="admin"
$env:UNIFI_PASSWORD="..."

python scripts/pull_nvr.py --start "2026-08-21 21:00" --end "2026-08-22 03:00"
python scripts/process_night.py --config config.yaml --force
python scripts/search_person.py --profile Marcus --start 21:00 --end 03:00
```

Frigate: set `nvr.type: frigate` and `nvr.port: 5000`.

---

## Setup (Windows)

```powershell
git clone -b windows https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# OSNet (accuracy lever on 3090)
pip install gdown
pip install git+https://github.com/KaiyangZhou/deep-person-reid.git

copy config.example.yaml config.yaml
```

Verify CUDA:

```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no gpu')"
```

---

## Other useful flags

```powershell
# Relative seconds instead of wall clock
python scripts/search_person.py --profile Marcus --start-s 0 --end-s 600

# Seed from an existing local track
python scripts/follow_person.py --seed-camera test_cam --seed-track 1 --name smoke_test --start-s 0 --end-s 120
```

Protect-style filenames (`...-Aug 21, 11:33 PM - Aug 21, 11:35 PM.mp4`) are parsed so `--start 23:33` maps to wall clock.

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

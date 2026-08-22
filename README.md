# AI No Key — **mac** branch

Tag someone. Search a time window. Get every appearance across cameras.

Apple Silicon (MPS). 32GB+ recommended.

---

## The loop you wanted

```bash
git pull
# still on branch mac

# 1) Tag a person in a frame (opens numbered crops)
python scripts/tag_person.py \
  --video "data/cameras/test_cam/yourclip.mp4" \
  --at 5

# 2) Enroll the one you picked
python scripts/tag_person.py \
  --video "data/cameras/test_cam/yourclip.mp4" \
  --at 5 --pick 0 --name Marcus --role hookah

# 3) Find them in a time period (uses detection cache)
python scripts/search_person.py --profile Marcus --start 21:00 --end 03:00
```

Open `data/output/trails/Marcus/report.html`.

`--end 03:00` after `--start 21:00` wraps overnight.

---

## Pull last night from UniFi Protect

Edit `config.yaml` → `nvr.host` + camera name map. Credentials via env is safer:

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
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

---

## Other useful flags

```bash
# Relative seconds instead of wall clock
python scripts/search_person.py --profile Marcus --start-s 0 --end-s 600

# Seed from an existing local track
python scripts/follow_person.py --seed-camera test_cam --seed-track 1 --name smoke_test --start-s 0 --end-s 120
```

Protect-style filenames (`...-Aug 21, 11:33 PM - Aug 21, 11:35 PM.mp4`) are parsed so `--start 23:33` maps to wall clock.

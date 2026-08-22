# AI No Key — Mac app (Dock icon)

## One-time setup

1. Clone the `mac` branch and run **Install AI No Key.command** (venv + OSNet).
2. Install Platypus:
   ```bash
   brew install --cask platypus
   ```
   Open Platypus once → Settings → **Install Command Line Tool**.
3. Double-click **Build AI No Key App.command**.

You get **AI No Key.app** in the project folder. Drag it to the Dock.

## How it works

The `.app` is a thin Platypus wrapper. It runs `scripts/app_launch.sh`, which:

- Finds the project folder (must stay next to the `.app`)
- Uses the project `.venv` (Python + OSNet + YOLO)
- Starts the local UI on http://127.0.0.1:8787
- Opens your browser

**Important:** Do not move only the `.app` without the rest of the folder. The models and config live in the project directory.

## Custom icon

1. Create a 1024×1024 PNG.
2. Convert to `.icns` (Xcode Asset Catalog, or `iconutil`, or an online converter).
3. Rebuild:
   ```bash
   platypus -a "AI No Key" -o "Text Window" -p /bin/bash \
     -V 1.0.0 -I com.sayless.ainokey \
     -c scripts/app_launch.sh -i YourIcon.icns -R -y "AI No Key.app"
   ```

## Without Platypus

You can still use **AI No Key.command** (double-click, no Dock icon packaging).

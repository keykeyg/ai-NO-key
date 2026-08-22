#!/bin/bash
# Builds AI No Key.app with a real Dock icon using Platypus.
# Run this once on your Mac after Install AI No Key.command.
cd "$(dirname "$0")"
set -e

clear 2>/dev/null || true
echo "========================================"
echo "  Build AI No Key.app"
echo "========================================"
echo ""

# Need Platypus CLI
if ! command -v platypus >/dev/null 2>&1; then
  echo "Platypus is not installed."
  echo ""
  echo "Install it with Homebrew:"
  echo "  brew install --cask platypus"
  echo ""
  echo "Then open Platypus once and install the command-line tool"
  echo "from Settings → Install Command Line Tool."
  echo ""
  echo "Or download: https://sveinbjorn.org/platypus"
  echo ""
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -f scripts/app_launch.sh ]; then
  echo "Missing scripts/app_launch.sh — are you in the project folder?"
  read -r -p "Press Return to close..."
  exit 1
fi

chmod +x scripts/app_launch.sh

OUT="AI No Key.app"
rm -rf "$OUT"

echo "Building $OUT ..."
echo ""

# Interface None = no terminal window, just runs in background-ish
# Text window is better so you can see server logs and Ctrl+C-equivalent quit
platypus \
  -a "AI No Key" \
  -o "Text Window" \
  -p "/bin/bash" \
  -V "1.0.0" \
  -u "Keyan" \
  -I "com.sayless.ainokey" \
  -c "scripts/app_launch.sh" \
  -R \
  -y \
  "$OUT"

echo ""
if [ -d "$OUT" ]; then
  echo "Done."
  echo ""
  echo "You now have:"
  echo "  $PWD/$OUT"
  echo ""
  echo "Drag it to your Dock or Applications."
  echo "Keep this whole project folder — the app needs the .venv next to it."
  echo ""
  echo "Optional: replace the icon"
  echo "  1. Make a 1024x1024 PNG"
  echo "  2. Convert to ICNS (Icon Composer / online tool)"
  echo "  3. Re-run this build with: platypus -i YourIcon.icns ..."
  echo ""
  open -R "$OUT"
else
  echo "Build failed."
fi

echo ""
read -r -p "Press Return to close..."

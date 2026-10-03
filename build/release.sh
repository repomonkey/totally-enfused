#!/bin/bash
# ============================================================
# Totally Enfused — build, sign, notarize, staple
# Usage: ./build/release.sh
#
# Prerequisites:
#   brew install create-dmg
#   pip install pyinstaller (in .venv)
#   Set the three variables below.
# ============================================================
set -euo pipefail

# Credentials live in build/release.env (gitignored):
#   APPLE_ID, TEAM_ID, SIGN_IDENTITY, APP_PASSWORD
source "$(dirname "$0")/release.env"

# ── Validate ────────────────────────────────────────────────
if [[ -z "$TEAM_ID" || -z "$APP_PASSWORD" ]]; then
  echo "ERROR: Set TEAM_ID and APP_PASSWORD in this script before running."
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
APP="$DIST/Totally Enfused.app"
DMG="$DIST/TotallyEnfused.dmg"

echo "==> Building frontend"
cd "$ROOT/frontend" && npm run build
cd "$ROOT"

echo "==> Running PyInstaller"
"$ROOT/.venv/bin/pip" install pyinstaller --quiet
"$ROOT/.venv/bin/pyinstaller" build/build_mac.spec \
  --distpath "$DIST" \
  --workpath "$ROOT/build/work" \
  --noconfirm

echo "==> Signing app (deep, hardened runtime)"
codesign --deep --force --options runtime \
  --entitlements "$ROOT/build/entitlements.plist" \
  --sign "$SIGN_IDENTITY" \
  "$APP"

echo "==> Verifying signature"
codesign --verify --deep --strict "$APP"
spctl --assess --type exec "$APP" || true   # may fail before notarization — that's fine

echo "==> Creating zip for notarization"
cd "$DIST"
ditto -c -k --keepParent "Totally Enfused.app" TotallyEnfused_notarize.zip

echo "==> Submitting to Apple Notarization (this takes a few minutes)"
xcrun notarytool submit TotallyEnfused_notarize.zip \
  --apple-id "$APPLE_ID" \
  --team-id "$TEAM_ID" \
  --password "$APP_PASSWORD" \
  --wait

echo "==> Stapling notarization ticket"
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"

echo "==> Creating DMG"
rm -f "$DMG"
create-dmg \
  --volname "Totally Enfused" \
  --volicon "$ROOT/assets/icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Totally Enfused.app" 150 185 \
  --hide-extension "Totally Enfused.app" \
  --app-drop-link 450 185 \
  --no-internet-enable \
  "$DMG" \
  "$APP"

codesign --sign "$SIGN_IDENTITY" "$DMG"

echo ""
echo "✓ Done: $DMG"
echo "  Distribute this file — users just drag to /Applications."

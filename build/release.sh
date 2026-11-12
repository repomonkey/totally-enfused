#!/bin/bash
# ============================================================
# Totally Enfused — build, sign, notarize, staple
# Usage: ./build/release.sh
#
# Prerequisites:
#   build/build_hugin_tools.sh has produced vendor/bundle
#   brew install create-dmg
#   pip install pyinstaller (in .venv)
# ============================================================
set -euo pipefail

# build/release.env (gitignored) sets SIGN_IDENTITY and NOTARY_PROFILE.
# The notarisation password lives in the keychain, stored once with:
#   xcrun notarytool store-credentials TotallyEnfused --apple-id <id> --team-id <team>
source "$(dirname "$0")/release.env"
NOTARY_PROFILE="${NOTARY_PROFILE:-TotallyEnfused}"

# ── Validate ────────────────────────────────────────────────
if ! xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null 2>&1; then
  echo "ERROR: keychain profile '$NOTARY_PROFILE' missing or rejected by Apple. Run:"
  echo "  xcrun notarytool store-credentials $NOTARY_PROFILE --apple-id <id> --team-id <team>"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
APP="$DIST/Totally Enfused.app"
VERSION=$(grep -o "'CFBundleShortVersionString': '[^']*'" "$ROOT/build/build_mac.spec" | cut -d"'" -f4)
DMG="$DIST/TotallyEnfused-$VERSION.dmg"

echo "==> Building frontend"
cd "$ROOT/frontend"
[ -d node_modules ] || npm ci
npm run build
cd "$ROOT"

echo "==> Running PyInstaller"
"$ROOT/.venv/bin/pip" install pyinstaller --quiet
"$ROOT/.venv/bin/pyinstaller" build/build_mac.spec \
  --distpath "$DIST" \
  --workpath "$ROOT/build/work" \
  --noconfirm

echo "==> Adding native Hugin tools"
B="$ROOT/vendor/bundle"
if [[ ! -x "$B/Helpers/enfuse" || ! -x "$B/Helpers/align_image_stack" ]]; then
  echo "ERROR: vendor/bundle missing — run build/build_hugin_tools.sh first"
  exit 1
fi
mkdir -p "$APP/Contents/Helpers" "$APP/Contents/Frameworks/hugin-libs" "$APP/Contents/Resources/ThirdParty"
cp "$B/Helpers/"* "$APP/Contents/Helpers/"
cp "$B/Frameworks/hugin-libs/"* "$APP/Contents/Frameworks/hugin-libs/"
cp -R "$B/licenses/"* "$APP/Contents/Resources/ThirdParty/"

echo "==> Adding ExifTool"
"$ROOT/.venv/bin/python" "$ROOT/build/bundle_exiftool.py" "$B"
cp -R "$B/exiftool" "$APP/Contents/Resources/exiftool"
cp -R "$B/licenses/"exiftool-* "$APP/Contents/Resources/ThirdParty/"
cp "$ROOT/build/THIRD_PARTY_NOTICES.md" "$APP/Contents/Resources/ThirdParty/"

echo "==> Signing Hugin tools (libraries first, then executables)"
for f in "$APP/Contents/Frameworks/hugin-libs/"*.dylib "$APP/Contents/Helpers/"*; do
  codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY" "$f"
done

echo "==> Signing app (deep, hardened runtime)"
codesign --deep --force --options runtime \
  --entitlements "$ROOT/build/entitlements.plist" \
  --sign "$SIGN_IDENTITY" \
  "$APP"

echo "==> Verifying signature"
codesign --verify --deep --strict "$APP"
spctl --assess --type exec "$APP" || true   # may fail before notarization — that's fine

echo "==> Self-test: full pipeline with motion handling inside the signed app"
"$APP/Contents/MacOS/Totally Enfused" --selftest

echo "==> Creating zip for notarization"
cd "$DIST"
ditto -c -k --keepParent "Totally Enfused.app" TotallyEnfused_notarize.zip

echo "==> Submitting to Apple Notarization (this takes a few minutes)"
xcrun notarytool submit TotallyEnfused_notarize.zip \
  --keychain-profile "$NOTARY_PROFILE" \
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

echo "==> Notarizing DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$DMG"

echo ""
echo "✓ Done: $DMG"
echo "  Distribute this file — users just drag to /Applications."

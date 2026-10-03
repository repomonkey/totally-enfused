#!/bin/bash
# Creates and installs a Finder Quick Action (right-click menu) that
# sends selected images to Totally Enfused via the URL scheme.
# Run once after installing the app.
set -euo pipefail

ACTION_NAME="Blend with Totally Enfused"
SERVICES_DIR="$HOME/Library/Services"
WORKFLOW="$SERVICES_DIR/${ACTION_NAME}.workflow"

mkdir -p "$WORKFLOW/Contents"

# ── document.wflow ───────────────────────────────────────────
cat > "$WORKFLOW/Contents/document.wflow" << 'WFLOW'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>AMApplicationBuild</key>
  <string>521.1</string>
  <key>AMApplicationVersion</key>
  <string>2.10</string>
  <key>AMDocumentVersion</key>
  <string>2</string>
  <key>actions</key>
  <array>
    <dict>
      <key>action</key>
      <dict>
        <key>AMAccepts</key>
        <dict>
          <key>Container</key>
          <string>List</string>
          <key>Optional</key>
          <false/>
          <key>Types</key>
          <array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>AMActionVersion</key>
        <string>2.0.3</string>
        <key>AMApplication</key>
        <array><string>Automator</string></array>
        <key>AMParameterProperties</key>
        <dict>
          <key>COMMAND_STRING</key>
          <dict/>
          <key>inputMethod</key>
          <dict/>
          <key>shell</key>
          <dict/>
          <key>source</key>
          <dict/>
        </dict>
        <key>AMProvides</key>
        <dict>
          <key>Container</key>
          <string>List</string>
          <key>Types</key>
          <array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>ActionBundlePath</key>
        <string>/System/Library/Automator/Run Shell Script.action</string>
        <key>ActionName</key>
        <string>Run Shell Script</string>
        <key>ActionParameters</key>
        <dict>
          <key>COMMAND_STRING</key>
          <string>python3 -c "
import sys, subprocess, urllib.parse
files = sys.argv[1:]
encoded = ','.join(urllib.parse.quote(f, safe='/') for f in files)
url = 'totallyenfused://blend?files=' + encoded
subprocess.run(['open', url])
" "$@"</string>
          <key>CheckedForUserDefaultShell</key>
          <true/>
          <key>inputMethod</key>
          <integer>1</integer>
          <key>shell</key>
          <string>/bin/bash</string>
          <key>source</key>
          <string></string>
        </dict>
        <key>BundleIdentifier</key>
        <string>com.apple.RunShellScript</string>
        <key>CFBundleVersion</key>
        <string>2.0.3</string>
        <key>CanShowSelectedItemsWhenRun</key>
        <false/>
        <key>CanShowWhenRun</key>
        <true/>
        <key>Category</key>
        <array><string>AMCategoryUtilities</string></array>
        <key>Class Name</key>
        <string>RunShellScriptAction</string>
        <key>InputUUID</key>
        <string>B8B49C28-6B3F-4A97-9F5E-123456789ABC</string>
        <key>Keywords</key>
        <array><string>Shell</string><string>Script</string><string>Run</string></array>
        <key>OutputUUID</key>
        <string>C9C59D39-7C4G-5B08-0G6F-234567890BCD</string>
        <key>UUID</key>
        <string>A7A38B17-5A2E-3986-8E4D-012345678ABC</string>
        <key>UnlocalizedApplications</key>
        <array><string>Automator</string></array>
        <key>arguments</key>
        <dict>
          <key>0</key>
          <dict>
            <key>default value</key>
            <integer>0</integer>
            <key>name</key>
            <string>inputMethod</string>
            <key>required</key>
            <string>0</string>
            <key>type</key>
            <string>0</string>
            <key>uuid</key>
            <string>0</string>
          </dict>
          <key>1</key>
          <dict>
            <key>default value</key>
            <string></string>
            <key>name</key>
            <string>COMMAND_STRING</string>
            <key>required</key>
            <string>0</string>
            <key>type</key>
            <string>0</string>
            <key>uuid</key>
            <string>1</string>
          </dict>
          <key>2</key>
          <dict>
            <key>default value</key>
            <string>/bin/sh</string>
            <key>name</key>
            <string>shell</string>
            <key>required</key>
            <string>0</string>
            <key>type</key>
            <string>0</string>
            <key>uuid</key>
            <string>2</string>
          </dict>
        </dict>
        <key>isViewVisible</key>
        <true/>
        <key>location</key>
        <string>309.000000:253.000000</string>
        <key>nibPath</key>
        <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
      </dict>
      <key>isViewVisible</key>
      <true/>
    </dict>
  </array>
  <key>connectors</key>
  <dict/>
  <key>workflowMetaData</key>
  <dict>
    <key>serviceInputTypeIdentifier</key>
    <string>com.apple.Automator.fileSystemObject.image</string>
    <key>serviceOutputTypeIdentifier</key>
    <string>com.apple.Automator.nothing</string>
    <key>serviceProcessesInput</key>
    <integer>0</integer>
    <key>systemImageName</key>
    <string>NSTouchBarColorPickerFill</string>
    <key>workflowTypeIdentifier</key>
    <string>com.apple.Automator.servicesMenu</string>
  </dict>
</dict>
</plist>
WFLOW

# ── Info.plist ───────────────────────────────────────────────
cat > "$WORKFLOW/Contents/Info.plist" << 'INFO'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSServices</key>
  <array>
    <dict>
      <key>NSMenuItem</key>
      <dict>
        <key>default</key>
        <string>Blend with Totally Enfused</string>
      </dict>
      <key>NSMessage</key>
      <string>runWorkflowAsService</string>
      <key>NSRequiredContext</key>
      <dict>
        <key>NSApplicationIdentifier</key>
        <string>com.apple.finder</string>
      </dict>
      <key>NSSendFileTypes</key>
      <array>
        <string>public.image</string>
        <string>public.camera-raw-image</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
INFO

# Reload services so it appears immediately
/System/Library/CoreServices/pbs -update 2>/dev/null || true

echo "✓ Quick Action installed: '${ACTION_NAME}'"
echo "  Right-click images in Finder → Quick Actions → '${ACTION_NAME}'"
echo "  (You may need to enable it in System Settings → Keyboard → Shortcuts → Services)"

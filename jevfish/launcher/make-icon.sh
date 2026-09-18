#!/bin/bash
# Rebuilds JevFish.app/Contents/Resources/AppIcon.icns from the header logo.
# Needs only macOS tools: Quick Look renders the SVG, sips resizes, iconutil packs.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../../JevFish.app/Contents/Resources/AppIcon.icns"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# Apple's grid: an 824 px tile on a 1024 px canvas. Dots shifted 1 unit right to sit centred.
cat >"$work/icon.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 32 32">
  <rect x="3.125" y="3.125" width="25.75" height="25.75" rx="5.8" fill="#0e5a6b"/>
  <g fill="#ffffff" transform="translate(16 16) scale(0.9) translate(-16 -16) translate(1 0)">
    <circle cx="9" cy="12" r="2.2"/><circle cx="15" cy="9" r="2.2"/><circle cx="15" cy="16" r="2.2"/>
    <circle cx="21" cy="12" r="2.2"/><circle cx="21" cy="19" r="2.2"/><circle cx="9" cy="20" r="2.2"/>
    <circle cx="15" cy="23" r="2.2"/>
  </g>
</svg>
SVG
qlmanage -t -s 1024 -o "$work" "$work/icon.svg" >/dev/null
mkdir "$work/AppIcon.iconset"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$work/icon.svg.png" --out "$work/AppIcon.iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$work/icon.svg.png" --out "$work/AppIcon.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$work/AppIcon.iconset" -o "$out"
cp "$work/icon.svg.png" "${JEVFISH_ICON_PREVIEW:-/dev/null}" 2>/dev/null || true
echo "wrote $out"

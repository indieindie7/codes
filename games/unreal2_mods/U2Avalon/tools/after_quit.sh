#!/bin/sh
# After the user quits Unreal II (2026-10-07 session): install the U2AvalonCards built in SystemBuild (per-map
# dressing, ClientTravel reload, clouds that grow and fade) and split the ini into family sections.
set -e
G="/c/Program Files (x86)/Steam/steamapps/common/Unreal II The Awakening"
T="$(cd "$(dirname "$0")" && pwd)"
R='C:\Users\john\Documents\U2_research\towns\TutA_Ridge5'
if tasklist | grep -qi 'Unreal2.exe'; then echo "the game is still running"; exit 1; fi
cp "$G/System/U2AvalonCards.u" "$G/System/U2AvalonCards.u.before-sets"
cp "$G/SystemBuild/U2AvalonCards.u" "$G/System/U2AvalonCards.u"
INI="$G/System/U2AvalonCards.ini"
cp "$INI" "$INI.before-sets"
# the session's live edits (the global section the game saved last) become TutA's own set
py -3.13 "$T/split_sets.py" "$INI" tuta "ini=$INI"
# TutA_Ridge5's layout into its own set (its cards, plumes, trucks, loudspeakers), the red beacon card left out
py -3.13 "$T/export_mutator.py" "$INI" shift=-5300 family=tuta_ridge5 "layout=$R\\isl_layout.json" "t3d=$TEMP\\r5_actors.t3d" "heightmap=$R\\isl_ec.bmp" props=0
py -3.13 "$T/motion.py" "$R\\isl_layout.json" "ini=$INI" family=tuta_ridge5
py -3.13 - "$INI" <<'EOF'
import re, sys
p = sys.argv[1]
t = open(p, newline="").read()
i = t.index("[tuta_ridge5 AvalonSet]")
t = t[:i] + re.sub(r"(?m)^Cards\[(\d+)\]=AvalonSM\.Cards\.BeaconTowerHY[^\r\n]*", r"Cards[\1]=", t[i:])
for k in ("Maps", "StormMaps"):
    t = re.sub(r"(?m)^(%s=(?![^\r\n]*tuta_ridge5\*)[^\r\n]*)" % k, r"\1,tuta_ridge5*", t, count=1)
open(p, "w", newline="").write(t)
EOF
grep -n '^\[' "$INI"
echo "installed: U2AvalonCards.u (backup .before-sets), ini split (backup U2AvalonCards.ini.before-sets)"

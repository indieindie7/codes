#!/bin/bash
# Retargets every generated death motion (kimodo_deaths.sh) into AdventMod/Anims as
# ModDie_<zone>_<take>.json. CPU only.
K=/c/Users/john/Documents/Tools/kimodo
HERE="$(cd "$(dirname "$0")" && pwd)"
for d in "$K"/out/deaths/*/; do
  zone=$(basename "$d"); n=0
  for f in "$d"*.npz; do
    "$K/venv/Scripts/python.exe" "$HERE/kimodo_retarget.py" "$f" "ModDie_${zone}_$n" | sed 's/.*Anims.//'
    n=$((n+1))
  done
done

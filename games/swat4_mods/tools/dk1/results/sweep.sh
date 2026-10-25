# DK1 gym sweep: single missions (eMapList 0), rush and pairs, 90 s cap each.
#   bash results/sweep.sh [out.jsonl] [map:brain ...]   (default: every 10th index x rush/pairs)
# A failed run (bridge timeout = "Game crashed :(" box) kills and relaunches the game before going on.
cd "$(dirname "$0")/.."
out=${1:-results/sweep.jsonl}; shift
cells="$*"
[ -z "$cells" ] && for i in 0 10 20 30 40 50 60 70 80 90 100 110 120; do cells="$cells $i:rush $i:pairs"; done
for c in $cells; do
  i=${c%%:*}; b=${c##*:}
  if ! py -3.13 -I dk1gym.py run 1 "$out" --brain $b --secs 90 --map 0/$i; then
    echo "{\"map\": \"0/$i\", \"brain\": \"$b\", \"error\": true}" >> "$out"
    taskkill //im DoorKickers.exe //f; sleep 6
    py -3.13 -I dk1gym.py launch; sleep 30
  fi
done
echo SWEEP DONE

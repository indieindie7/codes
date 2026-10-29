# DK1 gym sweep: single missions (eMapList 0), 90 s cap each.
#   bash results/sweep.sh [out.jsonl] [map:brain ...]   (default: every 10th index x rush/pairs)
# SKIP="30 80" env = map indices to skip. A failed run (bridge timeout) is retried once after killing + relaunching the game;
# a second failure is logged as an error row. If F: (USB enclosure with the game) disappears the sweep aborts.
cd "$(dirname "$0")/.."
out=${1:-results/sweep.jsonl}; shift
cells="$*"
[ -z "$cells" ] && for i in 0 10 20 30 40 50 60 70 80 90 100 110 120; do cells="$cells $i:rush $i:pairs"; done
relaunch() { taskkill //im DoorKickers.exe //f; sleep 6; py -3.13 -I dk1gym.py launch; sleep 30; }
for c in $cells; do
  i=${c%%:*}; b=${c##*:}
  case " $SKIP " in *" $i "*) continue;; esac
  [ -d /c/Games/DoorKickers ] || { echo "game dir GONE, abort"; exit 3; }
  ok=0
  for try in 1 2; do
    if py -3.13 -I dk1gym.py run 1 "$out" --brain $b --secs 90 --map 0/$i; then ok=1; break; fi
    [ -d /c/Games/DoorKickers ] || { echo "game dir GONE, abort"; exit 3; }
    relaunch
  done
  [ $ok = 1 ] || echo "{\"map\": \"0/$i\", \"brain\": \"$b\", \"error\": true}" >> "$out"
done
echo SWEEP DONE

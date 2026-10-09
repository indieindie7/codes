#!/bin/sh
# Mark watcher for the Claude chat: one line per new in-game request, with the picture to post into the chat.
#   MARK <n> | <note> | <screenshot png or sketch png>
#   SKETCH <name> | <note> | <sketch png>         (a sketch saved without a mark)
#   CHAT | <line>                                  (AvalonChat)
#   CRASH | <log line>
# Polls Unreal2.log every 3 s; a restarted game (shorter log) starts the count again.
L="/c/Program Files (x86)/Steam/steamapps/common/Unreal II The Awakening/System/Unreal2.log"
SK="C:\\Program Files (x86)\\Steam\\steamapps\\common\\Unreal II The Awakening\\System\\Sketch"
T="$(cd "$(dirname "$0")" && pwd)"
P='edit MARK|GM: SKETCH|AvalonChat|Unrecognized command|Critical:|General protection'
n0=$(grep -aEc "$P" "$L" 2>/dev/null || echo 0)
while true; do
	n=$(grep -aEc "$P" "$L" 2>/dev/null || echo 0)
	[ "$n" -lt "$n0" ] && n0=0
	if [ "$n" -gt "$n0" ]; then
		grep -aE "$P" "$L" | tail -n $((n - n0)) | while IFS= read -r line; do
			case "$line" in
			*"edit MARK"*)
				num=$(echo "$line" | sed -n 's/.*edit MARK \([0-9]*\).*/\1/p')
				note=$(echo "$line" | sed -n 's/.* note \(.*\)$/\1/p' | sed 's/ sketch:sketch-[0-9-]*$//')
				sk=$(echo "$line" | sed -n 's/.*sketch:\(sketch-[0-9-]*\).*/\1/p')
				if [ -n "$sk" ]; then pic="$SK\\$sk.png"
				else
					sleep 2
					pic=$(PYTHONUTF8=1 py "$T/live.py" --marks 1 2>/dev/null | sed -n 's/^ *shot: //p' | tail -1)
				fi
				echo "MARK $num | $note | $pic" ;;
			*"GM: SKETCH"*)
				sk=$(echo "$line" | sed -n 's/.*SKETCH \(sketch-[0-9-]*\).*/\1/p')
				note=$(echo "$line" | sed -n 's/.* note \(.*\)$/\1/p')
				echo "SKETCH $sk | $note | $SK\\$sk.png" ;;
			*AvalonChat*) echo "CHAT | $(echo "$line" | cut -c1-300)" ;;
			*Unrecognized*) echo "TYPED | $(echo "$line" | cut -c1-300)" ;;
			*) echo "CRASH | $(echo "$line" | cut -c1-300)" ;;
			esac
		done
		n0=$n
	fi
	sleep 3
done

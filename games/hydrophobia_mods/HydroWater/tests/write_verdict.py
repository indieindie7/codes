"""write_verdict.py <idea_id> <score_log>: copy the scorer's last VERDICT line into
Tools/llm/autorun/logs/idea<id>.verdict.json ({"gain","rows","note"}) for ops ideas.py."""
import json, os, re, sys
i, log = sys.argv[1], sys.argv[2]
out = os.path.expanduser(f"~/Documents/Tools/llm/autorun/logs/idea{i}.verdict.json")
m = re.findall(r"^VERDICT (\{.*\})\s*$", open(log, encoding="utf-8", errors="replace").read(), re.M)
v = json.loads(m[-1]) if m else {"gain": -1, "rows": 0}
v["note"] = f"score_irl: score {v.get('score')} gain {v.get('gain')} over {v.get('rows')} rows" if m else "scorer printed no VERDICT (failed run)"
json.dump(v, open(out, "w", encoding="utf-8")); print(out, v)

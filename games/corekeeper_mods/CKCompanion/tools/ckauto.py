"""Send instructions to the Core Keeper AutoPlayer and read its goal/task tree.
  ckauto.py "mine 3 copper then go home"   queue an instruction
  ckauto.py stop                           cancel everything, control back to you
  ckauto.py                                print status (goal tree, queue, recent events)
  ckauto.py --watch 30 "explore 3"         send, then print status every 5 s for 30 s
Grammar (split on , ; then and): mine|dig|get [N] [copper|tin|wall...], explore [N], fight|kill [N],
go to X Z, go home|core|base, wait N, stop."""
import sys, time, pathlib
D = pathlib.Path(r"C:\Program Files (x86)\Steam\steamapps\common\Core Keeper\BepInEx\ckauto")
args = sys.argv[1:]; watch = 0
if args[:1] == ["--watch"]: watch = int(args[1]); args = args[2:]
if args:
    with open(D / "inbox.txt", "a", encoding="utf-8") as f: f.write(" ".join(args) + "\n")
    print("sent:", " ".join(args)); time.sleep(1.2)
end = time.time() + watch
while True:
    print((D / "status.txt").read_text(encoding="utf-8") if (D / "status.txt").exists() else "no status yet (game not running?)")
    if time.time() >= end: break
    time.sleep(5); print("-" * 40)

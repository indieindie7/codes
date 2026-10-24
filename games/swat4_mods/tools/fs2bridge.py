"""Send TorqueScript lines to Frozen Synapse 2 through the smbridge file poll.

  py -3.13 -I fs2bridge.py 'SMB_out(Canvas.getContent().getName());'
  py -3.13 -I fs2bridge.py -f script.cs        (one statement per line)
  py -3.13 -I fs2bridge.py --install           copy bridge.cs + hook main.cs

Waits for the previous in.txt to be consumed, writes the new one, waits for
the game to eat it, prints the out.txt lines it added.
"""
import os, sys, time, shutil

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Frozen Synapse 2"
BR = os.path.join(GAME, "smbridge")
IN, OUT = os.path.join(BR, "in.txt"), os.path.join(BR, "out.txt")
HOOK = '\n// SwatMinds bridge (remove to undo; original in main.cs.orig)\nif (isFile("smbridge/bridge.cs")) exec("smbridge/bridge.cs");\n'


def install():
    os.makedirs(BR, exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(__file__), "fs2_bridge.cs"), os.path.join(BR, "bridge.cs"))
    main = os.path.join(GAME, "main.cs")
    if not os.path.exists(main + ".orig"):
        shutil.copy(main, main + ".orig")
    s = open(main, encoding="latin-1").read()
    if "smbridge" not in s:
        open(main, "a", encoding="latin-1").write(HOOK)
    print("installed; restart the game")


def wait_gone(timeout):
    t = time.time()
    while os.path.exists(IN):
        if time.time() - t > timeout:
            sys.exit("timeout: game not polling (minimized and throttled? not running?)")
        time.sleep(0.1)


def send(lines, timeout=60):
    wait_gone(timeout)
    n = sum(1 for _ in open(OUT, encoding="latin-1")) if os.path.exists(OUT) else 0
    open(IN + ".tmp", "w", encoding="latin-1").write("\n".join(lines) + "\n")
    os.replace(IN + ".tmp", IN)
    wait_gone(timeout)
    time.sleep(0.2)
    for l in open(OUT, encoding="latin-1").read().splitlines()[n:]:
        print(l)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--install":
        install()
    elif a and a[0] == "-f":
        send([l.strip() for l in open(a[1], encoding="latin-1") if l.strip()])
    else:
        send(a)

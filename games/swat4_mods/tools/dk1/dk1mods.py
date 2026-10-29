"""Enable DK1 mods by writing the <Mods path0=... /> list into the user's options.xml.
  py -3.13 -I dk1mods.py on [prefix]   all game mods/<prefix>* folders (default ws = workshop.py downloads)
  py -3.13 -I dk1mods.py off           remove the list
Paths need the trailing slash ("mods/ws<id>/"), else the log says "Could not find mod ... not there anymore".
Mod levels are appended to the map lists (single missions eMapList 0: 84 stock maps, mods from index 84)."""
import os, re, sys

GAME_MODS = os.path.join(os.environ.get("DK1_GAME", r"C:\Games\DoorKickers"), "mods")
OPTS = os.path.join(os.environ["USERPROFILE"], r"Documents\KillHouseGames\DoorKickers\options.xml")

if __name__ == "__main__":
    a = sys.argv[1:]
    txt = re.sub(r"\s*<Mods [^>]*/>", "", open(OPTS).read())
    if a and a[0] == "on":
        pre = a[1] if len(a) > 1 else "ws"
        ds = sorted(d for d in os.listdir(GAME_MODS)
                    if d.startswith(pre) and os.path.exists(os.path.join(GAME_MODS, d, "mod.xml")))
        attrs = " ".join(f'path{i}="mods/{d}/"' for i, d in enumerate(ds))
        txt = txt.replace("</Options>", f"    <Mods {attrs}/>\n</Options>")
        print(len(ds), "mods on")
    open(OPTS, "w").write(txt)

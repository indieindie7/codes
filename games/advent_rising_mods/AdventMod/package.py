"""Builds the release zips in Downloads: AdventMod-<ver>.zip (with the installer)
and AdventMod-<ver>-nexus.zip (no .bat files: Nexus quarantines them).
Run build.ps1 first so System\ has the compiled AdventMod.u and AdventNative.dll."""
import os, sys, zipfile

VER = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.expanduser("~"), "Downloads")
TOP = "AdventMod-" + VER
URL = "https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod"

files = [("System/AdventMod.u", "System/AdventMod.u"), ("System/AdventMod.int", "System/AdventMod.int"),
         ("System/AdventNative.dll", "System/AdventNative.dll"),
         ("Install AdventMod.bat", "Install AdventMod.bat"), ("Uninstall AdventMod.bat", "Uninstall AdventMod.bat"),
         ("native/adventnative.c", "Source/native/adventnative.c")]
files += [("Classes/" + f, "Source/Classes/" + f) for f in sorted(os.listdir(os.path.join(HERE, "Classes")))]
readme = open(os.path.join(HERE, "README.txt"), encoding="utf-8").read()
a, b = readme.index("Easy way:"), readme.index("Manual way:")
nexus_readme = readme[:a] + "The Install/Uninstall .bat that does all of this for you is in the GitHub\nversion: " + URL + "\n\n" + readme[b:]
a, b = nexus_readme.index('Double-click "Uninstall AdventMod.bat"'), nexus_readme.index("By hand: remove")
nexus_readme = nexus_readme[:a] + "Remove" + nexus_readme[b + len("By hand: remove"):]

for name, bats, text in ((TOP + ".zip", True, readme), (TOP + "-nexus.zip", False, nexus_readme)):
    path = os.path.join(OUT, name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in files:
            if dst.endswith(".bat") and not bats:
                continue
            z.write(os.path.join(HERE, src), TOP + "/" + dst)
        z.writestr(TOP + "/README.txt", text.replace("\r\n", "\n").replace("\n", "\r\n"))
    print(path, os.path.getsize(path))

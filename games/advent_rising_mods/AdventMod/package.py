"""Builds the release zips in Downloads: AdventMod-<ver>.zip (with the installer)
and AdventMod-<ver>-nexus.zip (no .bat files: Nexus quarantines them).
--graphics: AdventGraphicalMod-<ver>(-nexus).zip, the graphics-only edition for the
Nexus page of that name: System\AdventMod-graphics.u (build.ps1 -GraphicsOnly: gore,
armour and combat off by default) and no KarmaData.
Run build.ps1 first so System\\ has the compiled AdventMod.u and AdventNative.dll;
System\\d3d8.dll is the U2Shaders d3d8to9 build (github.com/indieindie7/d3d8to9,
branch gi-cascades) and U2Shaders\\ its shaders."""
import os, sys, zipfile

VER = "2.1"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.expanduser("~"), "Downloads")
GRAPHICS = "--graphics" in sys.argv
TOP = ("AdventGraphicalMod-" if GRAPHICS else "AdventMod-") + VER
URL = "https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod"

files = [("System/" + f, "System/" + f) for f in ("AdventMod.int", "AdventNative.dll", "d3d8.dll")]
files += [("System/AdventMod-graphics.u" if GRAPHICS else "System/AdventMod.u", "System/AdventMod.u")]
if not GRAPHICS:
    files += [("KarmaData/Advent.ka", "KarmaData/Advent.ka")]   # ragdoll skeletons, read from <game>\KarmaData
files += [("Install AdventMod.bat", "Install AdventMod.bat"), ("Uninstall AdventMod.bat", "Uninstall AdventMod.bat")]
# what the layer loads goes to System\U2Shaders; the scripts that generate files are source
for f in sorted(os.listdir(os.path.join(HERE, "U2Shaders"))):
    src = "U2Shaders/" + f
    if f.endswith(".py") or f == "terrain_src.hlsl":
        files.append((src, "Source/U2Shaders/" + f))
    else:
        files.append((src, "System/U2Shaders/" + f))
files += [("Licenses/" + f, "Licenses/" + f) for f in sorted(os.listdir(os.path.join(HERE, "Licenses")))]
files += [("native/" + f, "Source/native/" + f) for f in sorted(os.listdir(os.path.join(HERE, "native"))) if f.endswith(".c")]
files += [("Classes/" + f, "Source/Classes/" + f) for f in sorted(os.listdir(os.path.join(HERE, "Classes")))]

def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")

readme = open(os.path.join(HERE, "README.txt"), encoding="utf-8").read()
NL = "\r\n" if "\r\n" in readme else "\n"
if GRAPHICS:
    # the graphics edition: no Gore / armour sections, no KarmaData step, its own title
    a, b = readme.index("  Gore (new in 2.1)"), readme.index("  Fixes" + NL)
    readme = readme[:a] + readme[b:]
    a = readme.index("   Copy the zip's KarmaData folder")
    b = readme.index(NL, readme.index("KarmaData).", a)) + len(NL)
    readme = readme[:a] + readme[b:]
    readme = readme.replace(", delete" + NL + "KarmaData\\Advent.ka, and rename", ", and rename")
    title = readme.index("AdventMod 2.1 - shadows"); tend = readme.index(NL + NL, title)
    readme = ("AdventGraphicalMod 2.1 - shadows, post-processing and in-game options for Advent Rising" + NL
              + "=" * 87 + NL + NL
              + "(The graphics edition of AdventMod: the same files with the gore, armour and" + NL
              + "combat changes switched off. The full mod is on GitHub and on Nexus as AdventMod.)"
              + readme[tend:])
a, b = readme.index("Easy way:"), readme.index("Manual way:")
nexus_readme = readme[:a] + "The Install/Uninstall .bat that does all of this for you is in the GitHub\nversion: " + URL + "\n\n" + readme[b:]
a, b = nexus_readme.index('Double-click "Uninstall AdventMod.bat"'), nexus_readme.index("By hand: remove")
nexus_readme = nexus_readme[:a] + "Remove" + nexus_readme[b + len("By hand: remove"):]

u2ini = open(os.path.join(HERE, "System", "U2Shaders.ini"), encoding="ascii").read()

for name, bats, text in ((TOP + ".zip", True, readme), (TOP + "-nexus.zip", False, nexus_readme)):
    path = os.path.join(OUT, name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in files:
            if dst.endswith(".bat") and not bats:
                continue
            z.write(os.path.join(HERE, src), TOP + "/" + dst)
        z.writestr(TOP + "/System/U2Shaders.ini", crlf(u2ini))
        z.writestr(TOP + "/README.txt", crlf(text))
    print(path, os.path.getsize(path))

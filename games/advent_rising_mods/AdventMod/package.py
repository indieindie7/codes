"""Builds the release zips in Downloads: GoreOverhaul-<ver>.zip (the mod was AdventMod; its files keep that name) (with the installer)
and GoreOverhaul-<ver>-nexus.zip (no .bat files: Nexus quarantines them).
--graphics: AdventGraphicalMod-<ver>(-nexus).zip, the graphics-only edition for the
Nexus page of that name: System\\AdventMod-graphics.u (build.ps1 -GraphicsOnly: gore,
armour and combat off by default) and no KarmaData.
--check: run every refusal and README anchor lookup, list what would go in, write no zip.
--game <folder>: where build.ps1 wrote AdventMod\\Armour\\*.amesh (default: build.ps1's).
Run build.ps1 first (plain, no switch) so System\\ has the compiled AdventMod.u and
AdventNative.dll; System\\d3d8.dll is the U2Shaders d3d8to9 build
(github.com/indieindie7/d3d8to9, branch gi-cascades) and U2Shaders\\ its shaders.

Standing rule: no game texture pixels in a zip. So the U2Shaders folder goes in by an
explicit allow-list (SHADERS), the armour folder ships only *.amesh (geometry + one bit per
face; the *_faces.png / *_mask.png beside them are game pixels), and the pbr= rule for the
Gideon material map (a normal/roughness map computed from his skin texture) is dropped
from the shipped U2Shaders.ini together with its .dds."""
import os, sys, zipfile

VER = "3.0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.expanduser("~"), "Downloads")
GRAPHICS = "--graphics" in sys.argv
CHECK = "--check" in sys.argv
GAME = sys.argv[sys.argv.index("--game") + 1] if "--game" in sys.argv else r"H:\SteamLibrary\steamapps\common\Advent Rising"
TOP = ("AdventGraphicalMod-" if GRAPHICS else "GoreOverhaul-") + VER
URL = "https://github.com/indieindie7/codes/tree/master/games/advent_rising_mods/AdventMod"

# System\U2Shaders: what the layer loads, nothing else (no compiler dumps, previews, game-derived maps)
SHADERS = """AreaTexDX9.dds SMAA.hlsl SearchTex.dds atmos.hlsl blood_gloss.hlsl char_pbr.hlsl char_skin.hlsl
decal_parallax.hlsl gi.hlsl lut_advent.bmp lut_neutral.bmp pcss_map.hlsl pcss_proj.hlsl post_blur.hlsl
post_bright.hlsl post_down.hlsl post_final.hlsl post_up.hlsl rock_tone.hlsl sheen.hlsl sky_layer.hlsl
sky_tone.hlsl smaa_passes.hlsl soft.hlsl ssao.hlsl sss.hlsl terrain3.hlsl terrain4.hlsl terrain_detail.dds""".split()
SHADER_SOURCE = ["make_luts.py", "make_terrain.py", "make_terrain_detail.py", "terrain_src.hlsl"]
NOT_SHIPPED = ["gideon_uniform_pbr.dds"]           # derived from a game texture (tools/make_pbr_maps.py)
DROP_INI = ["pbr=2e106041 "]                      # the rule that uses it
ARMOUR_DIR = os.path.join(GAME, "AdventMod", "Armour")


def refuse(msg):
    sys.exit("package.py refuses: " + msg)


def contains(path, needle):
    with open(path, "rb") as f:
        return needle.encode() in f.read()


# refusals before anything else
ufile = "System/AdventMod-graphics.u" if GRAPHICS else "System/AdventMod.u"
# the plain build names the texture in ModJiggle's code ("SeekerSkinJ" twice); only the -JiggleSkin
# build carries the imported texture, whose source file name survives in the package
if contains(os.path.join(HERE, ufile), "seeker_infantry_filled"):
    refuse(ufile + " is a build.ps1 -JiggleSkin build (it carries the filled Seeker skin, a game texture).\n"
           "  Run build.ps1 with no switch (or -GraphicsOnly for the graphics edition) and try again.")
if not contains(os.path.join(HERE, "System", "d3d8.dll"), "atmos"):
    refuse("System\\d3d8.dll is a stale fork build (no atmos= code, which the shipped U2Shaders.ini turns on).\n"
           "  Copy the gi-cascades build (d3d8to9-gi\\bin\\Release\\d3d8.dll) into System\\ and try again.")
for f in SHADERS + SHADER_SOURCE:
    if not os.path.exists(os.path.join(HERE, "U2Shaders", f)):
        refuse("U2Shaders\\" + f + " is missing")
unknown = sorted(set(os.listdir(os.path.join(HERE, "U2Shaders"))) - set(SHADERS) - set(SHADER_SOURCE) - set(NOT_SHIPPED))
if unknown:
    print("note: not shipped from U2Shaders\\ (not in the allow-list):", ", ".join(unknown))
amesh = sorted(f for f in os.listdir(ARMOUR_DIR) if f.endswith(".amesh")) if os.path.isdir(ARMOUR_DIR) else []
if not GRAPHICS and not amesh:
    refuse("no *.amesh in " + ARMOUR_DIR + " (build.ps1 writes them; --game <folder> if the game is elsewhere)")

files = [("System/" + f, "System/" + f) for f in ("AdventMod.int", "AdventNative.dll", "d3d8.dll")]
files += [(ufile, "System/AdventMod.u")]
if not GRAPHICS:
    files += [("KarmaData/Advent.ka", "KarmaData/Advent.ka")]   # ragdoll skeletons, read from <game>\KarmaData
    files += [(os.path.join(ARMOUR_DIR, f), "AdventMod/Armour/" + f) for f in amesh]   # armour hit data, no pixels
files += [("Install AdventMod.bat", "Install AdventMod.bat"), ("Uninstall AdventMod.bat", "Uninstall AdventMod.bat")]
files += [("U2Shaders/" + f, "System/U2Shaders/" + f) for f in SHADERS]
files += [("U2Shaders/" + f, "Source/U2Shaders/" + f) for f in SHADER_SOURCE]
files += [("Licenses/" + f, "Licenses/" + f) for f in sorted(os.listdir(os.path.join(HERE, "Licenses")))]
files += [("native/" + f, "Source/native/" + f) for f in sorted(os.listdir(os.path.join(HERE, "native"))) if f.endswith(".c")]
files += [("Classes/" + f, "Source/Classes/" + f) for f in sorted(os.listdir(os.path.join(HERE, "Classes"))) if f.endswith(".uc")]
for src, dst in files:
    ext = os.path.splitext(dst)[1].lower()
    if ext in (".png", ".tga", ".jpg", ".bmp") and not dst.startswith("System/U2Shaders/lut_"):
        refuse("image file in the list: " + dst)


def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


readme = open(os.path.join(HERE, "README.txt"), encoding="utf-8").read()
NL = "\r\n" if "\r\n" in readme else "\n"
TITLE = "GoreOverhaul " + VER + " - gore"
if GRAPHICS:
    # the graphics edition: no Gore ... Death animations sections, no KarmaData / Armour steps, its own title
    a, b = readme.index("  Gore ("), readme.index("  Fixes" + NL)
    readme = readme[:a] + readme[b:]
    a = readme.index("   Copy the zip's KarmaData folder")
    b = readme.index(NL, readme.index("AdventMod\\Armour).", a)) + len(NL)
    readme = readme[:a] + readme[b:]
    readme = readme.replace(", delete" + NL + "KarmaData\\Advent.ka and the AdventMod folder, and rename", ", and rename")
    title = readme.index(TITLE); tend = readme.index(NL + NL, title)
    head = "AdventGraphicalMod " + VER + " - shadows, post-processing and in-game options for Advent Rising"
    readme = (head + NL + "=" * len(head) + NL + NL
              + "(The graphics edition of AdventMod: the same files with the gore, armour and" + NL
              + "combat changes switched off. The full mod is on GitHub and on Nexus as GoreOverhaul.)"
              + readme[tend:])
else:
    readme.index(TITLE)
a, b = readme.index("Easy way:"), readme.index("Manual way:")
nexus_readme = readme[:a] + "The Install/Uninstall .bat that does all of this for you is in the GitHub\nversion: " + URL + "\n\n" + readme[b:]
a, b = nexus_readme.index('Double-click "Uninstall AdventMod.bat"'), nexus_readme.index("By hand: remove")
nexus_readme = nexus_readme[:a] + "Remove" + nexus_readme[b + len("By hand: remove"):]

u2ini = open(os.path.join(HERE, "System", "U2Shaders.ini"), encoding="ascii").read()
kept = [l for l in u2ini.splitlines() if not any(l.startswith(d) for d in DROP_INI)]
if len(kept) == len(u2ini.splitlines()):
    print("note: no", DROP_INI, "line in System\\U2Shaders.ini (nothing dropped)")
u2ini = "\n".join(kept) + "\n"
for f in NOT_SHIPPED:
    if f in u2ini:
        refuse(f + " is still named in the shipped U2Shaders.ini")

if CHECK:
    print("check ok:", TOP, "(%d files, %d amesh)" % (len(files), len(amesh)))
    for src, dst in files:
        print("  " + dst)
    sys.exit(0)

for name, bats, text in ((TOP + ".zip", True, readme), (TOP + "-nexus.zip", False, nexus_readme)):
    path = os.path.join(OUT, name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in files:
            if dst.endswith(".bat") and not bats:
                continue
            z.write(src if os.path.isabs(src) else os.path.join(HERE, src), TOP + "/" + dst)
        z.writestr(TOP + "/System/U2Shaders.ini", crlf(u2ini))
        z.writestr(TOP + "/README.txt", crlf(text))
    print(path, os.path.getsize(path))

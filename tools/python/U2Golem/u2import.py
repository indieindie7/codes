"""Import a UT2004-style character into Unreal II as a Golem mesh, in one run.

    py -3.13 u2import.py NAME --psk mesh.psk --tex body.tga --tex head.tga [--psa anims.psa]

What you get: <game>\\Meshes\\NAME\\NAME.gem, compiled by `ucc make` into
Meshes\\GlmNAMEG.ugx + Textures\\GlmNAMET.utx. In game the mesh is GlmNAMEG.NAME; put it on
any human pawn (e.g. `hub dummy GlmNAMEG.NAME`) and it walks, aims and dies with the
marines' own animations.

Steps:
  1. prep.py: scale to Unreal II size, rename the skeleton to Unreal II's ("Merc ..."),
     turn the weapon bone into handpointR02, write plain TGA textures
  2. Golem Studio (driven by golem.py): new folder + file, import the PSK (and PSA),
     point each material at its texture, point the blueprint at the marines' shared
     animations (ArmorAnimsScripts) with their OriginScale, save
  3. ucc make

It uses the real mouse for a few minutes: don't touch the PC while it runs.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from golem import Golem, no_bgproxy, GAME, MESHES, SYSTEM     # noqa: E402
from prep import prepare, ORIGIN_SCALE                        # noqa: E402

WORK = os.path.join(os.path.expanduser("~"), "Documents", "U2Golem")
WORKSPACE = os.path.join(WORK, "U2Import.gws")
SHARED_SCRIPTS = ["Characters", "Biped", "ArmorAnims.gem", "Entity Scripts", "ArmorAnimsScripts"]   # the marines' animations


def write_workspace():
    os.makedirs(WORK, exist_ok=True)
    with open(WORKSPACE, "w", newline="") as f:
        f.write("[Workspace]\r\nRootFolder=%s\r\nTitle=Unreal II import\r\nTexturesRoot=%s\r\n" % (MESHES, MESHES))


def ucc_make(name, log):
    for old in (os.path.join(MESHES, "Glm%sG.ugx" % name), os.path.join(GAME, "Textures", "Glm%sT.utx" % name)):
        if os.path.exists(old):
            os.remove(old)
    r = subprocess.run([os.path.join(SYSTEM, "ucc.exe"), "make"], cwd=SYSTEM, capture_output=True, text=True, errors="replace")
    ok = "Success" in r.stdout and os.path.exists(os.path.join(MESHES, "Glm%sG.ugx" % name))
    log("ucc make: " + ("ok" if ok else "FAILED\n" + r.stdout[-2000:]))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="character name: folder, .gem and blueprint name (letters/digits)")
    ap.add_argument("--psk", required=True)
    ap.add_argument("--tex", action="append", default=[], help="one per material, in the PSK's material order")
    ap.add_argument("--psa", help="also import these animations as the character's own scripts")
    ap.add_argument("--own-anims", action="store_true", help="keep the imported PSA as the blueprint's scripts instead of sharing the marines'")
    ap.add_argument("--keep-open", action="store_true", help="leave Golem Studio running afterwards")
    a = ap.parse_args(argv)
    log = print
    name = a.name
    folder = os.path.join(MESHES, name)
    if os.path.exists(os.path.join(folder, name + ".gem")):
        sys.exit(f"{folder}\\{name}.gem already exists: delete that folder first to re-import")

    work = os.path.join(WORK, "work", name)
    psk, psa, texs, scale = prepare(a.psk, work, name, a.tex, a.psa, log=log)
    write_workspace()

    with no_bgproxy():
        g = Golem(WORKSPACE, log=log)
        try:
            root = g.tree.roots()[0].text().rstrip(" *")
            g.new_folder(root, name)
            g.new_file([root, name], name)
            for t in texs:
                shutil.copy(os.path.join(work, t + ".tga"), folder)
            gem = [root, name, name + ".gem"]
            log(g.import_psk_psa(gem, psk, name).strip())
            if psa:
                log(g.import_psk_psa(gem, psa, name, name + "Hierarchy", name + "Scripts").strip())
            log("textures: %s" % g.set_stage_textures(gem + ["Materials", name + "Materials"], {}))
            g.set_blueprint(gem + ["Entity Blueprint", name], None if a.own_anims else SHARED_SCRIPTS,
                            [("OriginScale", ORIGIN_SCALE), ("OriginTranslateY", -4.0)])   # as the marines have
            g.save(gem)
            log("saved %s (%d bytes)" % (os.path.join(folder, name + ".gem"), os.path.getsize(os.path.join(folder, name + ".gem"))))
        finally:
            if not a.keep_open:
                g.quit()
    ok = ucc_make(name, log)
    log(("done: in game the mesh is Glm%sG.%s" % (name, name)) if ok else "the build failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Import several UT2004 characters in a row (each gets its own folder and package).

    py -3.13 batch.py [NAME ...]      default: the test set below
"""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import u2import                      # noqa: E402
from golem import MESHES             # noqa: E402

EXTRACT = os.path.join(os.path.expanduser("~"), "Documents", "UT2004_extract", "psk")
SKINS = os.path.join(EXTRACT, "PlayerSkins", "Texture")

# name: (mesh .psk under the extract, [textures in material order])
CHARACTERS = {
    "Malcolm":     ("HumanMaleA/SkeletalMesh/MercMaleD.psk",   ["MercMaleDBodyA", "MercMaleDHeadA"]),
    "MercMaleA":   ("HumanMaleA/SkeletalMesh/MercMaleA.psk",   ["MercMaleABodyA", "MercMaleAHeadA"]),
    "NightMaleA":  ("HumanMaleA/SkeletalMesh/NightMaleA.psk",  ["NightMaleABodyA", "NightMaleAHeadA"]),
    "EgyptMaleA":  ("HumanMaleA/SkeletalMesh/EgyptMaleA.psk",  ["EgyptMaleABodyA", "EgyptMaleAHeadA"]),
    "MercFemaleA": ("HumanFemaleA/SkeletalMesh/MercFemaleA.psk", ["MercFemaleABodyA", "MercFemaleAHeadA"]),
    "AlienMaleA":  ("Aliens/SkeletalMesh/AlienMaleA.psk",      ["AlienMaleABodyA", "AlienMaleAHeadA"]),
    "BotA":        ("Bot/SkeletalMesh/BotA.psk",               ["BotABodyA", "BotAHeadA"]),
    "JuggMaleA":   ("Jugg/SkeletalMesh/JuggMaleA.psk",         ["JuggMaleABodyA", "JuggMaleAHeadA"]),
}
TEST_SET = ["MercMaleA", "NightMaleA", "EgyptMaleA", "MercFemaleA", "AlienMaleA", "BotA", "JuggMaleA"]


def main(names):
    results = {}
    for name in names:
        psk, texs = CHARACTERS[name]
        folder = os.path.join(MESHES, name)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        args = [name, "--psk", os.path.join(EXTRACT, psk)]
        for t in texs:
            args += ["--tex", os.path.join(SKINS, t + ".tga")]
        print("=" * 20, name, "=" * 20, flush=True)
        t0 = time.time()
        try:
            rc = u2import.main(args)
            results[name] = "ok" if rc == 0 else "build failed"
        except Exception as e:                     # keep going with the rest
            results[name] = "error: %s" % e
            try:
                import golem
                golem.kill()
            except Exception:
                pass
        print("%s: %s (%.0f s)" % (name, results[name], time.time() - t0), flush=True)
    print("\nsummary:", results)


if __name__ == "__main__":
    main(sys.argv[1:] or TEST_SET)

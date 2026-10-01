"""U2SoftShadows 2.0 options page: the add-on's settings become THE Shadows page.

Replaces the game's own Options > Shadows page (engine shadow detail, blob/blur,
etc.: the add-on draws every character shadow now) with the add-on's settings,
and removes what earlier versions added (the extra SOFTSHADOWS page, the OPEN
cross-links, the contact/hard-to-soft/capsule/varied-lights rows).

Patches UIScripts/ModMenus.ui + U2Menus.ui and System/ModMenus.int + U2Menus.int.
Idempotent; backups *.before-ssv2 on first run; --undo restores them.

    py -3.13 ssmenu_v2.py [GAME_DIR] [--undo]
"""
import os, shutil, sys

GAME = next((a for a in sys.argv[1:] if not a.startswith("--")),
            r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening")
FILES = [os.path.join(GAME, "UIScripts", n + ".ui") for n in ("ModMenus", "U2Menus")] + \
        [os.path.join(GAME, "System", n + ".int") for n in ("ModMenus", "U2Menus")]

# (row, key, label, tooltip, widget lines)
ROWS = [
    # U2Wardrobe's character dropdown shares the MISC page (first row: its list opens downward)
    ("WardrobeOutfit", "Character Model:",
     "Who you play as: Dalton, or one of the imported human characters. Also used in cutscenes.",
     ["U2Selector:{y}", "	Group=OptionWidgets_SHADOWS", "	Accessor=WardrobeMenuHelper,GetOutfitList",
      "	Modifier=WardrobeMenuHelper,SetOutfit", "	CurrentText=WardrobeMenuHelper,GetOutfit"]),
    ("SSEnabled", "Character Shadows:",
     "Soft multi-light character shadows. Off = the game's original single shadow.",
     ["U2CheckBox:{y}", "\tObject=SSMenuHelper", "\tVariable=Enabled"]),
    ("SSMaxShadows", "Lights per Character:",
     "How many lights cast a shadow of each character. More = heavier.",
     ["U2Slider:{y}", "\tRange=0,4", "\tStep=1", "\tFormat=Int2Format", "\tObject=SSMenuHelper", "\tVariable=MaxShadows"]),
    ("SSPlayerShadows", "Lights for Dalton:",
     "How many lights cast your own character's shadow (seen in third person, mirrors and the like).",
     ["U2Slider:{y}", "\tRange=1,6", "\tStep=1", "\tFormat=Int2Format", "\tObject=SSMenuHelper", "\tVariable=PlayerShadows"]),
    ("SSStrength", "Darkness:",
     "How dark the shadows are at full strength.",
     ["U2Slider:{y}", "\tRange=60,255", "\tStep=5", "\tFormat=Int4Format", "\tObject=SSMenuHelper", "\tVariable=Strength"]),
    ("SSFadeLength", "Fade Length:",
     "How far a shadow reaches before fading out, as a multiple of its length. 1 = gone at the head, 3 = gentle.",
     ["U2Slider:{y}", "\tRange=1,6", "\tStep=0.5", "\tFormat=Float2Format", "\tObject=SSMenuHelper", "\tVariable=FadeLength"]),
    ("SSRespectBaked", "Blend with Lighting:",
     "Shadows are as dark as their light's share of all the light around: in a brightly lit room the other lights fill them in.",
     ["U2CheckBox:{y}", "\tObject=SSMenuHelper", "\tVariable=RespectBaked"]),
    ("SSCameraCull", "Camera Culling:",
     "Only characters the camera can see get shadows. Recommended.",
     ["U2CheckBox:{y}", "\tObject=SSMenuHelper", "\tVariable=CameraCull"]),
    ("SSNearDistance", "Full Detail Within:",
     "Characters closer than this get every shadow; between this and the next distance, one shadow.",
     ["U2Slider:{y}", "\tRange=300,2000", "\tStep=50", "\tFormat=Int4Format", "\tObject=SSMenuHelper", "\tVariable=NearDistance"]),
    ("SSMidDistance", "Reduced Detail Within:",
     "Beyond this distance characters cast no shadow.",
     ["U2Slider:{y}", "\tRange=500,4000", "\tStep=100", "\tFormat=Int4Format", "\tObject=SSMenuHelper", "\tVariable=MidDistance"]),
]


def block_bounds(lines, header, end_pred):
    """[start, end) of a section starting at `header`, ending where end_pred(line) (exclusive)."""
    s = lines.index(header)
    e = s + 1
    while e < len(lines) and not end_pred(lines[e]):
        e += 1
    return s, e


def patch_ui(text):
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    # 1) no SOFTSHADOWS page state / transition
    lines = [l for l in lines if "OptionMenu:SOFTSHADOWS/" not in l and "Transition=Options.SoftShadows" not in l]
    # 2) remove the old add-on page blocks (keep the helper registration)
    for hdr in ("[OptionDescriptions_SOFTSHADOWS]", "[OptionWidgets_SOFTSHADOWS]"):
        if hdr in lines:
            s, e = block_bounds(lines, hdr, lambda l: l.startswith("Register=") or l.startswith("["))
            if e < len(lines) and lines[e].startswith("Register="):
                e += 1
            del lines[s:e]
    if "### U2SoftShadows options page ###" in lines:
        lines.remove("### U2SoftShadows options page ###")
    if "[WardrobeMenuHelper]" not in lines:
        i = lines.index("[OptionWidgets_SHADOWS]")
        lines[i:i] = ["[WardrobeMenuHelper]", "Helper=U2Wardrobe$WardrobeMenuHelper", "RegisterObj=WardrobeMenuHelper", ""]
    if "[SSMenuHelper]" not in lines:
        i = lines.index("[OptionWidgets_SHADOWS]")
        lines[i:i] = ["[SSMenuHelper]", "Helper=U2SoftShadows$SSMenuHelper", "RegisterObj=SSMenuHelper", ""]
    # 3) the Shadows page: descriptions
    s, e = block_bounds(lines, "[OptionDescriptions_SHADOWS]", lambda l: l.strip() == "" or l.startswith("["))
    desc = ["[OptionDescriptions_SHADOWS]", "Class=FixedSizeContainer", "Location=%0%,%1%",
            "Component=OptionMouseOvers:SHADOWS"]
    for n, (key, _, _, _) in enumerate(ROWS):
        desc.append("Component=OptionDescription:%02d/%d/%s" % (n + 1, n * 26, key))
    lines[s:e] = desc
    # 4) the Shadows page: widgets
    s, e = block_bounds(lines, "[OptionWidgets_SHADOWS]", lambda l: l.startswith("Register=OptionWidgets_SHADOWS"))
    w = ["[OptionWidgets_SHADOWS]", "Class=FixedSizeContainer", "Component=SSMenuHelper", "Component=WardrobeMenuHelper"]
    for n, (_, _, _, wl) in enumerate(ROWS):
        w.append("Component=" + wl[0].format(y=n * 26))
        w += wl[1:]
    w.append("Location=%0%,%1%")
    lines[s:e] = w
    return nl.join(lines)


def patch_int(text):
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    stale = ("OptionDescriptionSS", "MouseOver_SOFTSHADOWS_", "SubTitleSoftShadows=", "OptionButtonSSOpen=")
    at = None
    out = []
    for l in lines:
        if l.startswith(stale) or l.startswith("MouseOver_SHADOWS_") or l.startswith("OptionDescriptionWardrobe"):
            if at is None and l.startswith(stale):
                at = len(out)
            continue
        out.append(l)
    new = []
    for n, (key, label, tip, _) in enumerate(ROWS):
        new.append("OptionDescription%s=%s" % (key, label))
    for n in range(12):
        new.append("MouseOver_SHADOWS_%02d=%s" % (n + 1, ROWS[n][2] if n < len(ROWS) else ""))
    if at is None:
        at = next(i for i, l in enumerate(out) if l.startswith("SubTitleShadows=")) + 1
    out[at:at] = new
    return nl.join(out)


def main():
    undo = "--undo" in sys.argv
    for f in FILES:
        bak = f + ".before-ssv2"
        if undo:
            if os.path.exists(bak):
                shutil.copyfile(bak, f)
                print("restored", f)
            continue
        if not os.path.exists(bak):
            shutil.copyfile(f, bak)
        text = open(bak, encoding="latin-1", newline="").read()
        text = patch_ui(text) if f.endswith(".ui") else patch_int(text)
        open(f, "w", encoding="latin-1", newline="").write(text)
        print("patched", f)


if __name__ == "__main__":
    main()

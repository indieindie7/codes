r"""Tell U2GM when Unreal II's console opens or closes (for the d3d8 fork's sketch tool, sketch=1).

U2's console is a UI component (UIScripts\Console.ui, a MultiStateComponent), so script can't see it.
This adds TriggerEvent lines to its two consoles; the UI runs them as console commands on every state
change (the same form ModMenus.ui uses for "UIOPENMAP ..."):

    [Console]        TriggerEvent=1,0,ConsoleCommand,gm con big 1     (the full console, ~)
                     TriggerEvent=0,0,ConsoleCommand,gm con big 0
    [QuickConsole]   TriggerEvent=1,0,ConsoleCommand,gm con quick 1   (the one-line console, Tab)
                     TriggerEvent=0,0,ConsoleCommand,gm con quick 0

GMMaster keeps that as con=N in PanelState (System\U2GM.ini); the fork shows its Sketch strip.

    py sketch_console_ui.py                 patch <game>\UIScripts\Console.ui (backup: Console.ui.before-sketch)
    py sketch_console_ui.py --dry-run       print the patched file, write nothing
    py sketch_console_ui.py --undo          put the backup back
    py sketch_console_ui.py --file PATH     another Console.ui (a copy, for testing)

Idempotent: a file that already has the lines is left alone. Run it while the game is closed (the UI
scripts are read at start). Without U2GM loaded the lines only log "Unrecognized command" (harmless).
"""
import os, shutil, sys

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
MARK = "gm con "
ADD = {
    "console": ["TriggerEvent=1,0,ConsoleCommand,gm con big 1", "TriggerEvent=0,0,ConsoleCommand,gm con big 0"],
    "quickconsole": ["TriggerEvent=1,0,ConsoleCommand,gm con quick 1", "TriggerEvent=0,0,ConsoleCommand,gm con quick 0"],
}


def patch(text):
    """the file's text with the trigger lines after each section's last Transition= line"""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    out, section, pending = [], None, None
    done = set()

    def flush():
        nonlocal pending
        if pending is not None:
            out[pending + 1:pending + 1] = ADD[section]
            done.add(section)
            pending = None

    for line in lines:
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            flush()
            section = s[1:-1].lower()
        out.append(line)
        if section in ADD and s.lower().startswith("transition="):
            pending = len(out) - 1
    flush()
    missing = set(ADD) - done
    if missing:
        raise SystemExit("no Transition= line found in section(s) %s: not patched" % ", ".join(sorted(missing)))
    return nl.join(out)


def main(argv):
    path = os.path.join(GAME, "UIScripts", "Console.ui")
    if "--file" in argv:
        path = argv[argv.index("--file") + 1]
    backup = path + ".before-sketch"
    if "--undo" in argv:
        if not os.path.exists(backup):
            raise SystemExit("no backup %s" % backup)
        shutil.copyfile(backup, path)
        print("restored", path, "from", backup)
        return
    text = open(path, "rb").read().decode("latin1")
    if MARK in text:
        print("already patched:", path)
        return
    new = patch(text)
    if "--dry-run" in argv:
        print(new)
        return
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(new.encode("latin1"))
    os.replace(tmp, path)
    print("patched", path, "(backup", backup + ")")


if __name__ == "__main__":
    main(sys.argv[1:])

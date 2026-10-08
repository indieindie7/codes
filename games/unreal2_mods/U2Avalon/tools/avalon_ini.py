r"""U2AvalonCards.ini edits confined to one section.

Since 2026-10-07 each Avalon map family keeps its own dressing in its own section (U2AvalonCards'
AvalonSet.uc, perobjectconfig). U2 names that section after the OBJECT only, in the case of the name already in the
name table: [TutA], [TutA_Ridge5] (seen in the game's own save) - so pass the map's own spelling. The global [U2AvalonCards.AvalonCards] keeps the shared settings and is what a family with no
section yet starts from. family=None writes the global section (the old behaviour).
"""
import re

GLOBAL = "U2AvalonCards.AvalonCards"


def section_name(family):
    return GLOBAL if not family else family


def edit(ini, family, drop_keys, lines, used=True):
    """in the family's section: remove every line whose key (before '=' and any [index]) is in drop_keys,
    then add lines (strings 'Key=Value'); the section is created if missing"""
    txt = open(ini, newline="").read().replace("\r\n", "\n")
    name = section_name(family)
    find = re.compile(r"(?mi)^\[%s\]\n" % re.escape(name))      # the game's spelling may differ in case
    if not find.search(txt):
        txt = txt.rstrip("\n") + "\n\n[%s]\n" % name
    i = find.search(txt).end()
    m = re.search(r"(?m)^\[", txt[i:])
    j = i + m.start() if m else len(txt)
    body = txt[i:j]
    keep = []
    for line in body.split("\n"):
        k = re.match(r"([A-Za-z_]\w*)", line)
        if k and k.group(1) in drop_keys:
            continue
        if family and line.startswith("bUsed="):
            continue
        keep.append(line)
    new = [l + "\n" for l in lines]
    if family and used:
        new.insert(0, "bUsed=True\n")
    body = "".join(new) + "\n".join(keep)
    if not body.endswith("\n"):
        body += "\n"
    txt = txt[:i] + body + txt[j:]
    open(ini, "w", newline="").write(txt.replace("\n", "\r\n"))

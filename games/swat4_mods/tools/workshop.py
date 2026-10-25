"""Steam Workshop fetcher without a Steam login, for gym maps (DK1 248610, FS2 445020).

  py -3.13 -I workshop.py list <appid> [pages] [tag]       top-rated items: id, tags, size, title
  py -3.13 -I workshop.py get <appid> <dest> [pages] [tag]  download each item's file into <dest>/<id>/

Uses the public browse page for ids and ISteamRemoteStorage/GetPublishedFileDetails (no key) for
file_url. Only legacy-UGC items carry a file_url; items without one need the Steam client (subscribe).
"""
import json, os, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def ids(appid, pages=1, tag=None):
    out = []
    for p in range(1, pages + 1):
        q = dict(appid=appid, browsesort="toprated", actualsort="toprated", section="readytouseitems", p=p, numperpage=30)
        if tag:
            q["requiredtags[]"] = tag
        html = get("https://steamcommunity.com/workshop/browse/?" + urllib.parse.urlencode(q)).decode("utf-8", "replace")
        new = [i for i in dict.fromkeys(re.findall(r"filedetails/\?id=(\d+)", html)) if i not in out]
        if not new:
            break
        out += new
    return out


def details(id_list):
    res = []
    for k in range(0, len(id_list), 50):
        chunk = id_list[k:k + 50]
        form = {"itemcount": len(chunk), **{f"publishedfileids[{i}]": v for i, v in enumerate(chunk)}}
        d = json.loads(get("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
                           urllib.parse.urlencode(form).encode()).decode("utf-8"))
        res += d["response"].get("publishedfiledetails", [])
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    mode, appid = a[0], a[1]
    if mode == "list":
        pages, tag = int(a[2]) if len(a) > 2 else 1, a[3] if len(a) > 3 else None
    else:
        dest = a[2]
        pages, tag = int(a[3]) if len(a) > 3 else 1, a[4] if len(a) > 4 else None
    items = details(ids(appid, pages, tag))
    for x in items:
        tags = ",".join(t["tag"] for t in x.get("tags", []))
        line = f"{x['publishedfileid']} [{tags}] {x.get('file_size')} {'url' if x.get('file_url') else 'NOURL'} {x.get('title', '')[:50]}"
        if mode == "list":
            print(line)
            continue
        if not x.get("file_url"):
            print("skip", line); continue
        d = os.path.join(dest, x["publishedfileid"])
        os.makedirs(d, exist_ok=True)
        fn = os.path.join(d, os.path.basename(x.get("filename") or "item.bin") or "item.bin")
        if not os.path.exists(fn):
            open(fn, "wb").write(get(x["file_url"]))
        json.dump({k: x.get(k) for k in ("publishedfileid", "title", "tags", "file_size", "time_updated")},
                  open(os.path.join(d, "info.json"), "w"), indent=1)
        print("ok", line)

"""vidmotion: see movement in a gameplay recording as still images.

  strip  - frames STEP seconds apart, side by side (read a motion frame by frame)
  ghost  - the same frames blended into one image, older ones fainter (motion trails;
           best with a still camera, or crop to the moving thing)
  sheet  - one ghost every EVERY seconds over the whole video, tiled

  py -3 vidmotion.py strip  video.mp4 --at 12.5 [--count 8 --step 0.1 --crop x,y,w,h --width 320] -o out.png
  py -3 vidmotion.py ghost  video.mp4 --at 12.5 [--count 8 --step 0.067 --crop ...] -o out.png
  py -3 vidmotion.py sheet  video.mp4 [--every 2 --count 6 --step 0.1 --cols 6 --width 384] -o out.png

Times may be a list: --at 3.2,8.6,10 makes one row per time (strip) or one tile per time (ghost).
Needs ffmpeg (FFMPEG env var, PATH, or the winget Gyan.FFmpeg install).
"""
import argparse, glob, os, shutil, subprocess, sys


def ffmpeg():
    p = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if p:
        return p
    hits = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))
    if hits:
        return sorted(hits)[-1]
    sys.exit("ffmpeg not found (set FFMPEG)")


def run(args):
    r = subprocess.run([ffmpeg(), "-v", "error", "-y"] + args)
    if r.returncode:
        sys.exit("ffmpeg failed")


def pre(a):
    """crop + scale filters for one frame"""
    f = []
    if a.crop:
        x, y, w, h = a.crop.split(",")
        f.append(f"crop={w}:{h}:{x}:{y}")
    f.append(f"scale={a.width}:-2")
    return f


def window(a, t):
    """input args and select filter for count frames step apart from t"""
    span = a.count * a.step + 0.5
    return ["-ss", f"{max(t, 0):.3f}", "-t", f"{span:.3f}", "-i", a.video], f"fps={1 / a.step:.4f}"


def ghost_filter(a):
    # weights rise with time: the newest frame is solid, older ones fade
    w = " ".join(str(i + 1) for i in range(a.count))
    return f"tmix=frames={a.count}:weights='{w}'"


def strip(a, times, out):
    ins, fl = [], []
    for i, t in enumerate(times):
        x, sel = window(a, t)
        ins += x
        fl.append(f"[{i}:v]{sel}," + ",".join(pre(a)) + f",tile={a.count}x1,trim=end_frame=1[r{i}]")
    if len(times) > 1:
        fl.append("".join(f"[r{i}]" for i in range(len(times))) + f"vstack=inputs={len(times)}[o]")
    else:
        fl[-1] = fl[-1].replace("[r0]", "[o]")
    run(ins + ["-filter_complex", ";".join(fl), "-map", "[o]", "-frames:v", "1", out])


def ghost(a, times, out, cols, pad=False):
    ins, fl = [], []
    for i, t in enumerate(times):
        x, sel = window(a, t)
        ins += x
        fl.append(f"[{i}:v]{sel}," + ",".join(pre(a)) + f",{ghost_filter(a)},trim=start_frame={a.count - 1}:end_frame={a.count},setpts=PTS-STARTPTS[g{i}]")
    n = len(times)
    if n == 1:
        fl[-1] = fl[-1].replace("[g0]", "[o]")
    else:
        rows = (n + cols - 1) // cols
        # xstack layout: x_y in units of the first tile
        layout = "|".join(("0" if i % cols == 0 else "+".join(["w0"] * (i % cols))) + "_" +
                          ("0" if i // cols == 0 else "+".join(["h0"] * (i // cols))) for i in range(n))
        fl.append("".join(f"[g{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[o]")
    if pad and n < cols:
        fl[-1] = fl[-1][:-3] + f"[p];[p]pad={cols * a.width}:ih[o]"
    run(ins + ["-filter_complex", ";".join(fl), "-map", "[o]", "-frames:v", "1", out])


def duration(video):
    probe = ffmpeg().replace("ffmpeg", "ffprobe")
    r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["strip", "ghost", "sheet"])
    p.add_argument("video")
    p.add_argument("--at", default="0")
    p.add_argument("--count", type=int, default=8)
    p.add_argument("--step", type=float, default=0.1)
    p.add_argument("--crop")
    p.add_argument("--width", type=int, default=320)
    p.add_argument("--every", type=float, default=2.0)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("-o", "--out", required=True)
    a = p.parse_args()
    times = [float(x) for x in a.at.split(",")]
    if a.mode == "strip":
        strip(a, times, a.out)
    elif a.mode == "ghost":
        ghost(a, times, a.out, a.cols)
    else:
        d = duration(a.video)
        ts, t = [], 0.0
        while t + a.count * a.step < d:
            ts.append(t)
            t += a.every
        # many inputs at once is slow to seek: do it in rows
        rows = []
        for r in range(0, len(ts), a.cols):
            name = f"{a.out}.row{r // a.cols}.png"
            ghost(a, ts[r:r + a.cols], name, a.cols, pad=True)
            rows.append(name)
        if len(rows) == 1:
            os.replace(rows[0], a.out)
        else:
            run(sum((["-i", n] for n in rows), []) + ["-filter_complex",
                "".join(f"[{i}:v]" for i in range(len(rows))) + f"vstack=inputs={len(rows)}", a.out])
            for n in rows:
                os.remove(n)
    print(a.out)


if __name__ == "__main__":
    main()

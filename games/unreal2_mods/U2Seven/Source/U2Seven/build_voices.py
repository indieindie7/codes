"""Voice The Seven with Piper and write the UnrealScript that plays it.

    python build_voices.py            synthesize changed lines, write Classes/SevenScript.uc
    python build_voices.py --all      re-synthesize every line
    python build_voices.py --sample   one line per character to Sounds/_samples/

Each character has a Piper voice and an effect chain:
  radio      band-limited, a little overdriven, hiss, squelch clicks (the crew)
  clean      no radio at all, a touch of room (Hawkins: he sounds like he is
             in the room; everyone else sounds far away)
  recording  narrow, crackling, drop-outs (found logs: Meyer, Isaak's last log)
Ne'Ban is pitched down for an alien timbre.

Output: 22050 Hz mono 16-bit WAVs in Sounds/, imported by #exec lines in
Classes/SevenScript.uc, which also holds every line's text, speaker and
length for the SevenStory mutator.
"""
import hashlib, json, math, os, sys, wave
import numpy as np
from piper import PiperVoice
from piper.config import SynthesisConfig

from story import EPISODES, MUTE

DIALOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Dialog")

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = r"C:\Users\john\Documents\Tools\piper_voices"
SOUNDS = os.path.join(HERE, "Sounds")
SR = 22050
RNG = np.random.default_rng(7)

CAST = {
    #            voice model                          speed  semitones  effect
    "DALTON":    ("en_US-john-medium",                 1.12,  -1.0,     "radio"),
    "AIDA":      ("en_US-lessac-medium",               0.97,   0.0,     "radio"),
    "NEBAN":     ("en_US-hfc_male-medium",             0.95,  -3.0,     "radio"),
    "ISAAK":     ("en_GB-northern_english_male-medium", 1.10, -1.5,     "radio_heavy"),
    "ISAAK_LOG": ("en_GB-northern_english_male-medium", 1.15, -1.5,     "recording"),
    "HAWKINS":   ("en_GB-alan-medium",                 1.05,   0.0,     "clean"),
    "MEYER":     ("en_US-amy-medium",                  1.05,   0.0,     "recording"),
}
SUBTITLE_NAME = {"ISAAK_LOG": "ISAAK (log)", "NEBAN": "NE'BAN"}

_voices = {}


def voice(name):
    if name not in _voices:
        _voices[name] = PiperVoice.load(os.path.join(VOICES, name + ".onnx"))
    return _voices[name]


def synth(model, text, speed):
    v = voice(model)
    cfg = SynthesisConfig(length_scale=speed, noise_scale=0.6, noise_w_scale=0.7)
    chunks = [c.audio_float_array for c in v.synthesize(text, syn_config=cfg)]
    x = np.concatenate(chunks).astype(np.float64)
    sr = v.config.sample_rate
    return resample(x, sr, SR)


def resample(x, sr_in, sr_out):
    if sr_in == sr_out:
        return x
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def pitch_shift(x, semitones):
    """Lower/raise pitch by resampling (also changes length; the speed setting
    in CAST compensates)."""
    if not semitones:
        return x
    f = 2 ** (semitones / 12.0)
    return np.interp(np.arange(0, len(x) - 1, f), np.arange(len(x)), x)


def band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def noise(n, lo=1000, hi=6000):
    return band(RNG.standard_normal(n), lo, hi)


def norm(x, peak=0.7):
    m = np.max(np.abs(x)) or 1
    return x * peak / m


def squelch(n=int(0.07 * SR)):
    s = noise(n, 800, 5000)
    return norm(s * np.linspace(1, 0.2, n), 0.25)


def fx_radio(x, drive=2.2, hiss=0.012):
    x = norm(band(x, 300, 3400))
    x = np.tanh(x * drive) / np.tanh(drive)
    pad = np.zeros(int(0.08 * SR))
    y = np.concatenate([squelch(), pad, x, pad, squelch()])
    y = y + hiss * noise(len(y), 500, 7000) / (np.std(noise(1000)) + 1e-9) * 0.05
    return y


def fx_clean(x):
    # a little room: short decaying noise impulse response, mixed low
    ir_len = int(0.22 * SR)
    ir = RNG.standard_normal(ir_len) * np.exp(-np.linspace(0, 7, ir_len))
    dry = np.concatenate([x, np.zeros(ir_len)])
    wet = np.zeros(len(dry))
    c = np.convolve(x, ir)[:len(dry)]
    wet[:len(c)] = c
    return norm(dry) + 0.10 * norm(wet)


def fx_recording(x):
    x = norm(band(x, 450, 2800))
    x = np.tanh(x * 1.6)
    # crackle and a few drop-outs
    y = x + 0.02 * noise(len(x), 1500, 8000) / 0.05
    for _ in range(max(1, len(y) // SR)):
        i = RNG.integers(0, max(1, len(y) - 2000))
        y[i:i + int(RNG.integers(300, 1500))] *= 0.15
    clicks = RNG.integers(0, len(y), size=len(y) // 900)
    y[clicks] += RNG.choice([-0.5, 0.5], size=len(clicks))
    return y


EFFECTS = {"radio": fx_radio, "radio_heavy": lambda x: fx_radio(x, 3.2, 0.03),
           "clean": fx_clean, "recording": fx_recording}


def static_burst(seconds):
    n = int(seconds * SR)
    s = noise(n, 400, 7000)
    env = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.05 * SR))
    flutter = 0.6 + 0.4 * np.abs(np.sin(np.arange(n) / SR * 2 * math.pi * 7))
    return norm(s * env * flutter, 0.35)


def write_wav(path, x):
    x = np.clip(norm(x, 0.8) * 32767, -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())
    return len(x) / SR


def render(speaker, text):
    model, speed, semis, effect = CAST[speaker]
    x = synth(model, text, speed)
    x = pitch_shift(x, semis)
    return EFFECTS[effect](x)


def uc_string(s):
    return s.replace('"', "'")


def main():
    force = "--all" in sys.argv
    os.makedirs(SOUNDS, exist_ok=True)
    if "--sample" in sys.argv:
        os.makedirs(os.path.join(SOUNDS, "_samples"), exist_ok=True)
        for who in CAST:
            write_wav(os.path.join(SOUNDS, "_samples", who + ".wav"),
                      render(who, "Marshal. The coordinates are ready when you are."))
        print("samples written")
        return

    cache_path = os.path.join(SOUNDS, "_cache.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) and not force else {}
    execs, props, statics = [], [], {}
    k = 0
    for e in EPISODES:
        cues = [(0, 0.0, e["intro"])] + [(i + 1, float(d), lines) for i, (d, lines) in enumerate(e["mids"])]
        for cue, delay, lines in cues:
            for j, (who, what) in enumerate(lines):
                if who == "BEAT":
                    snd, dur, name, text = "None", float(what), "", ""
                elif who == "STATIC":
                    key = "Static%02d" % round(float(what) * 10)
                    if key not in statics:
                        statics[key] = write_wav(os.path.join(SOUNDS, key + ".wav"), static_burst(float(what)))
                        execs.append(f"#exec AUDIO IMPORT FILE=Sounds\\{key}.wav NAME={key} GROUP=Radio")
                    snd, dur, name, text = f"Sound'{key}'", statics[key], "", ""
                else:
                    key = "E%dC%d_%02d" % (e["ep"], cue, j)
                    path = os.path.join(SOUNDS, key + ".wav")
                    sig = hashlib.md5(f"{who}|{what}|{CAST[who]}".encode()).hexdigest()
                    if cache.get(key, {}).get("sig") != sig or not os.path.exists(path):
                        dur = write_wav(path, render(who, what))
                        cache[key] = {"sig": sig, "dur": dur}
                        print("voiced", key, who, what[:50])
                    dur = cache[key]["dur"]
                    execs.append(f"#exec AUDIO IMPORT FILE=Sounds\\{key}.wav NAME={key} GROUP=VO")
                    snd, name, text = f"Sound'{key}'", SUBTITLE_NAME.get(who, who), what
                props.append(f'\tLines({k})=(Ep={e["ep"]},Cue={cue},CueDelay={delay:.1f},Speaker="{uc_string(name)}",'
                             f'Text="{uc_string(text)}",Snd={snd},Dur={dur:.2f})')
                k += 1
    json.dump(cache, open(cache_path, "w"), indent=1)

    maps = [f'\tEpisodeMaps({i})=(Ep={e["ep"]},Map="{m}")' for i, (e, m) in
            enumerate((e, m) for e in EPISODES for m in e["maps"])]
    # every node of the dialogue files to silence
    muted = []
    for folder, files in MUTE:
        for f in files:
            for line in open(os.path.join(DIALOG, folder, f + ".dlg"), encoding="latin-1"):
                line = line.strip()
                if line.startswith("[") and line.endswith("]") and line[1:-1] != "Root":
                    muted.append(line[1:-1])
    maps += [f'\tMutedNodes({i})="{n}"' for i, n in enumerate(muted)]
    uc = ["//=============================================================================",
          "// SevenScript - GENERATED by build_voices.py from story.py. Do not edit.",
          "// Every line of The Seven: speaker, subtitle, sound, length; the cue it",
          "// belongs to (0 = the episode's intro, 1+ = mid-mission cues) and, for a",
          "// cue's first line, how many seconds after the intro it starts.",
          "//=============================================================================",
          "class SevenScript extends Info;", ""] + execs + ["",
          "struct SevenLine", "{", "\tvar int Ep, Cue;", "\tvar float CueDelay;", "\tvar string Speaker, Text;",
          "\tvar Sound Snd;", "\tvar float Dur;", "};", "",
          "struct EpisodeMap", "{", "\tvar int Ep;", "\tvar string Map;", "};", "",
          "var array<SevenLine> Lines;", "var array<EpisodeMap> EpisodeMaps;",
          "var array<string> MutedNodes;      // original dialogue nodes silenced (see story.MUTE)", "",
          "defaultproperties", "{"] + props + maps + ["}"]
    os.makedirs(os.path.join(HERE, "Classes"), exist_ok=True)
    open(os.path.join(HERE, "Classes", "SevenScript.uc"), "w", encoding="utf-8", newline="\n").write("\n".join(uc) + "\n")
    print("%d entries, %d voiced lines, %.0f s of audio" % (k, len([c for c in cache]), sum(c["dur"] for c in cache.values())))


if __name__ == "__main__":
    main()

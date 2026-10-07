r"""The Liandri public address: binder/pa_lines.md -> loudspeaker WAVs for U2AvalonCards (AvalonPA).

    py tools/pa_voice.py [out dir ...]

Piper TTS (Documents\Tools\piper_voices) speaks each line; then it is made to sound like a company
loudspeaker heard across a town: a two-tone chime first, telephone band (300-3400 Hz), a little clipping,
and two late echoes off the halls. 22.05 kHz 16-bit mono, the format UnrealEd's AUDIO IMPORT takes.
"""
import os, re, subprocess, sys, tempfile, wave

import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES = r"C:\Users\john\Documents\Tools\piper_voices"
SR = 22050


def lines():
    txt = open(os.path.join(HERE, "binder", "pa_lines.md"), encoding="utf-8").read()
    voice = re.search(r"(?m)^voice:\s*(\S+)", txt).group(1)
    return voice, re.findall(r"(?m)^(pa\d+)\s*\|\s*(.+)$", txt)


def speak(voice, text):
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "s.wav")
        subprocess.run([sys.executable, "-m", "piper", "-m", os.path.join(VOICES, voice + ".onnx"), "-f", out,
                        "--length-scale", "1.08"], input=text.encode("utf-8"), check=True, capture_output=True)
        w = wave.open(out)
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
        w.close()
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    return a


def chime():
    t = np.arange(int(0.55 * SR)) / SR
    env = np.exp(-t * 5)
    a = np.zeros(int(1.3 * SR))
    for k, f in enumerate((880.0, 659.3)):          # down a fourth: "ding-dong"
        s = 0.35 * env * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t))
        a[int(k * 0.45 * SR):int(k * 0.45 * SR) + len(s)] += s
    return a


def loudspeaker(a):
    a = sosfilt(butter(4, [300, 3400], "bandpass", fs=SR, output="sos"), a)
    a = np.tanh(a * 2.2) / np.tanh(2.2)               # a cheap horn speaker
    out = np.zeros(len(a) + int(0.9 * SR))
    out[:len(a)] += a
    for d, g in ((0.19, 0.35), (0.43, 0.2)):          # off the halls across the yard
        i = int(d * SR)
        out[i:i + len(a)] += g * sosfilt(butter(2, 2000, "lowpass", fs=SR, output="sos"), a)
    return out


def write(path, a):
    a = a / max(1e-6, np.abs(a).max()) * 0.9
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((a * 32767).astype("<i2").tobytes())
    w.close()


if __name__ == "__main__":
    outs = sys.argv[1:] or [os.path.join(os.path.dirname(HERE), "U2AvalonCards", "Source", "U2AvalonCards", "Sounds")]
    voice, rows = lines()
    for d in outs:
        os.makedirs(d, exist_ok=True)
    for pid, text in rows:
        a = np.concatenate([chime(), np.zeros(int(0.25 * SR)), speak(voice, text)])
        a = loudspeaker(a)
        for d in outs:
            write(os.path.join(d, pid.upper() + ".wav"), a)
        print(pid, "%.1f s" % (len(a) / SR), text[:60])

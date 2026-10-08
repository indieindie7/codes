"""Shared bits for VoiceSplice: paths, audio I/O, text normalisation, phonemes, frame features.

No audio or extracted game text ever lives next to this code. Everything a run makes goes under
VOICESPLICE_HOME (default %USERPROFILE%\\Documents\\VoiceSplice), which is outside git.
"""
import json
import os
import re
import subprocess
import unicodedata
import wave

import numpy as np

HOME = os.environ.get("VOICESPLICE_HOME", os.path.join(os.path.expanduser("~"), "Documents", "VoiceSplice"))
U2_GAME = os.environ.get("U2_GAME", r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening")
TOOLS = os.path.join(os.path.expanduser("~"), "Documents", "Tools")
WHISPER_PY = os.path.join(TOOLS, "whisper", "Scripts", "python.exe")
PIPER_VOICES = os.path.join(TOOLS, "piper_voices")
# voice conversion (stage 2): kNN-VC runs in the CPU-PyTorch venv; weights and feature caches live on H:
VC_PY = os.environ.get("VOICESPLICE_VC_PY", os.path.join(TOOLS, "visualqa", "Scripts", "python.exe"))
MODELS = os.environ.get("VOICESPLICE_MODELS", r"H:\VoiceSplice\models")
CACHE = os.environ.get("VOICESPLICE_CACHE", r"H:\VoiceSplice\cache")
SR = 22050          # working rate (Piper's rate; plenty for speech). Game Ogg is written at 44.1 kHz.
HERE = os.path.dirname(os.path.abspath(__file__))


def bank_dir(name):
    d = os.path.join(HOME, "banks", name)
    os.makedirs(os.path.join(d, "clips"), exist_ok=True)
    return d


# ---------------------------------------------------------------- audio I/O

def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def decode(path, sr=SR):
    """Any audio file -> mono float32 at sr (via ffmpeg)."""
    p = subprocess.run([ffmpeg_exe(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path, x, sr=SR):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    y = np.clip(np.asarray(x, dtype=np.float32), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def write_ogg(path, x, sr=SR, out_sr=44100, quality=5):
    """Ogg Vorbis like the game's own Voice\\*.ogg (44.1 kHz mono)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcm = np.clip(np.asarray(x, dtype=np.float32), -1, 1).tobytes()
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
                    "-ar", str(out_sr), "-c:a", "libvorbis", "-q:a", str(quality), path], input=pcm, check=True)


def jl_read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def jl_write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- text

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
        "sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_words(n):
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + num_words(n % 100))
    if n < 1000000:
        return num_words(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + num_words(n % 1000))
    return " ".join(_ONES[int(c)] for c in str(n))


def norm_word(w):
    """Bank key for a word: lower case, ascii, apostrophes kept inside words (ne'ban, don't)."""
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode().lower()
    w = re.sub(r"[^a-z0-9']", "", w).strip("'")
    return w


def tokenize(text):
    """Text -> list of (word_key, punctuation_after). Numbers become words."""
    text = re.sub(r"\d+", lambda m: " " + num_words(m.group()) + " ", text)
    text = text.replace("-", " ")
    out = []
    for m in re.finditer(r"([A-Za-z0-9'\u00C0-\u024F]+)([^A-Za-z0-9'\u00C0-\u024F]*)", text):
        k = norm_word(m.group(1))
        if not k:
            continue
        p = m.group(2).strip()
        punct = "." if any(c in p for c in ".!") else "?" if "?" in p else "," if any(c in p for c in ",;:") else ""
        out.append((k, punct))
    return out


# ---------------------------------------------------------------- phonemes (eSpeak NG through Piper's bridge)

_MULTI = ["aɪ", "aʊ", "eɪ", "oʊ", "ɔɪ", "əʊ", "tʃ", "dʒ", "ɪə", "eə", "ʊə", "ɑː", "iː", "uː", "ɔː", "ɜː", "ɛː", "ɐ"]
VOWELS = set("aeiouæɐɑɒɔəɚɛɜɝɪʊʌyøœɨʉᵻ")
_ESPEAK = None
_PCACHE = {}


def _espeak():
    global _ESPEAK
    if _ESPEAK is None:
        from piper import espeakbridge
        from piper.phonemize_espeak import ESPEAK_DATA_DIR
        espeakbridge.initialize(str(ESPEAK_DATA_DIR))
        espeakbridge.set_voice("en-us")
        _ESPEAK = espeakbridge
    return _ESPEAK


def split_ipa(s):
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[ˈˌ\-_ .,!?;:]", "", s)
    out, i = [], 0
    while i < len(s):
        for m in sorted(_MULTI, key=len, reverse=True):
            if s.startswith(m, i):
                out.append(m)
                i += len(m)
                break
        else:
            c = s[i]
            if c in "ːˑ" and out:
                out[-1] += "ː"
            elif c == "̃" or unicodedata.combining(c):
                if out:
                    out[-1] += c
            else:
                out.append(c)
            i += 1
    # fold length marks so 'iː' and 'i' share units (length is a duration matter, not identity)
    return [p.replace("ː", "") or p for p in out]


def phonemes(word):
    """IPA phoneme list for one word key."""
    if word not in _PCACHE:
        es = _espeak()
        es.set_voice("en-us")              # Piper's synthesize() may have switched the shared espeak voice
        ipa = "".join(p for p, _, _ in es.get_phonemes(word.replace("'", "") if word.endswith("'") else word))
        _PCACHE[word] = split_ipa(ipa)
    return _PCACHE[word]


def is_vowel(p):
    return p[0] in VOWELS


def expected_dur(p):
    """Rough phone duration prior in seconds."""
    if len(p) > 1 and is_vowel(p) and is_vowel(p[-1]):
        return 0.13
    if is_vowel(p):
        return 0.085
    if p in ("p", "t", "k", "b", "d", "ɡ", "g", "ʔ", "ɾ"):
        return 0.06
    if p in ("s", "z", "ʃ", "ʒ", "f", "v", "θ", "ð", "h", "tʃ", "dʒ"):
        return 0.09
    return 0.06


# ---------------------------------------------------------------- frame features

HOP = 0.005


def frames(x, sr, win=0.025, hop=HOP):
    n, h = int(win * sr), int(hop * sr)
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    idx = np.arange(0, len(x) - n + 1, h)
    return np.stack([x[i:i + n] for i in idx]), h


def rms_track(x, sr):
    f, _ = frames(x, sr)
    return np.sqrt((f ** 2).mean(axis=1) + 1e-10)


def f0_track(x, sr, fmin=70, fmax=400):
    """Normalised-autocorrelation pitch per 5 ms frame (40 ms window); 0 = unvoiced."""
    f, _ = frames(x, sr, win=0.04)
    f = f - f.mean(axis=1, keepdims=True)
    lo, hi = int(sr / fmax), int(sr / fmin)
    nfft = 1 << int(np.ceil(np.log2(f.shape[1] * 2)))
    spec = np.fft.rfft(f * np.hanning(f.shape[1]), nfft)
    ac = np.fft.irfft(np.abs(spec) ** 2, nfft)[:, :hi + 1]
    ac = ac / (ac[:, :1] + 1e-9)
    lag = lo + np.argmax(ac[:, lo:hi + 1], axis=1)
    peak = ac[np.arange(len(lag)), lag]
    energy = np.sqrt((f ** 2).mean(axis=1))
    voiced = (peak > 0.45) & (energy > 0.01)
    f0 = np.where(voiced, sr / lag, 0.0)
    # remove octave spikes with a 5-frame median over voiced runs
    out = f0.copy()
    for i in range(len(f0)):
        if f0[i] > 0:
            w = f0[max(0, i - 2):i + 3]
            w = w[w > 0]
            out[i] = np.median(w)
    return out


_MEL = {}


def mfcc(x, sr, n_mfcc=13, n_mels=26):
    f, _ = frames(x, sr)
    nfft = 512 if sr <= 22050 else 1024
    p = np.abs(np.fft.rfft(f * np.hamming(f.shape[1]), nfft)) ** 2
    key = (sr, nfft, n_mels)
    if key not in _MEL:
        mel = lambda h: 2595 * np.log10(1 + h / 700)
        imel = lambda m: 700 * (10 ** (m / 2595) - 1)
        pts = imel(np.linspace(mel(60), mel(sr / 2 - 200), n_mels + 2))
        bins = np.floor((nfft + 1) * pts / sr).astype(int)
        fb = np.zeros((n_mels, nfft // 2 + 1))
        for m in range(1, n_mels + 1):
            a, b, c = bins[m - 1], bins[m], bins[m + 1]
            fb[m - 1, a:b] = (np.arange(a, b) - a) / max(1, b - a)
            fb[m - 1, b:c] = (c - np.arange(b, c)) / max(1, c - b)
        _MEL[key] = fb
    from scipy.fft import dct
    return dct(np.log(p @ _MEL[key].T + 1e-10), type=2, axis=1, norm="ortho")[:, :n_mfcc]


def semitones(a, b):
    return 12 * np.log2(a / b) if a > 0 and b > 0 else 0.0

# Solus exclusive-fullscreen removal patcher. Works on the Steamless-unpacked exe.
# usage: py -3.13 solus_patch.py apply|undo [exe]   (default: game exe)
import sys
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\TheSolusProject\Solus\Binaries\Win64\Solus-Win64-Shipping.exe"
# (file offset, old, new, what)
P = [
 (0x7a573d, "0fb64577", "31c09090", "D3D11Viewport ctor: bIsFullscreen(+0x54)=0 instead of param"),
 (0x7bfb6c, "40887754", "c6475400", "D3D11Viewport::Resize: store bIsFullscreen=0 (was sil)"),
 (0x7bfb64, "40387754", "44387f54", "Resize: compare member with r15b(0) so no reset loop"),
 (0x7bfb21, "7441",     "eb41",     "Resize: skip ResizeTarget(fullscreen mode) block"),
 (0x7a8b71, "0fb65654", "33d26690", "ResetSwapChainInternal: SetFullscreenState Fullscreen arg = 0"),
 (0x7bdc63, "410fb65654", "33d20f1f00", "ResetSwapChainInternal (inlined copy): Fullscreen arg = 0"),
]
mode = sys.argv[1] if len(sys.argv) > 1 else ""
exe = sys.argv[2] if len(sys.argv) > 2 else EXE
if mode not in ("apply", "undo"): sys.exit(__doc__)
d = bytearray(open(exe, "rb").read())
for off, old, new, what in P:
    o, n = bytes.fromhex(old), bytes.fromhex(new)
    want, other = (o, n) if mode == "apply" else (n, o)
    cur = bytes(d[off:off+len(o)])
    if cur == other: print("already", mode, hex(off)); continue
    if cur != want: sys.exit("MISMATCH at %x: %s (expected %s) - nothing written" % (off, cur.hex(), want.hex()))
for off, old, new, what in P:
    o, n = bytes.fromhex(old), bytes.fromhex(new)
    d[off:off+len(o)] = n if mode == "apply" else o
open(exe, "wb").write(d)
print(mode, "ok", len(P), "patches")

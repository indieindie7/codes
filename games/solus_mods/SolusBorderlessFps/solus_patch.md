# Solus exclusive-fullscreen removal (unpacked exe, file offsets)
Source: Solus-Win64-Shipping.exe, SteamStub 3.1 x64 removed with Steamless (copy in solus_work\solus.exe.unpacked.exe, never publish).
Apply/undo: py -3.13 solus_patch.py apply|undo [exe]. Original packed exe: Solus-Win64-Shipping.exe.bak-1115 in game folder.
Idea: FD3D11Viewport member +0x54 (bIsFullscreen) is forced 0 everywhere, so Windowed=!bIsFullscreen at swapchain creation is 1 and SetFullscreenState(TRUE) is never reached. Calls to SetFullscreenState (vtable 0x50) also get edx=0.

| offset | old | new | what |
|---|---|---|---|
| 0x7a573d | 0fb64577 | 31c09090 | viewport ctor: bIsFullscreen = 0 |
| 0x7bfb6c | 40887754 | c6475400 | Resize: store bIsFullscreen = 0 |
| 0x7bfb64 | 40387754 | 44387f54 | Resize: compare vs 0 (no reset loop) |
| 0x7bfb21 | 7441 | eb41 | Resize: skip ResizeTarget fullscreen-mode block |
| 0x7a8b71 | 0fb65654 | 33d26690 | ResetSwapChain: Fullscreen arg 0 |
| 0x7bdc63 | 410fb65654 | 33d20f1f00 | inlined ResetSwapChain: Fullscreen arg 0 |

Not done: EWindowMode Fullscreen->WindowedFullscreen mapping. Unpatched: wrapper at 0x176c540 (call [rcx+0x60]->vt 0x50, passthrough args, unknown class).

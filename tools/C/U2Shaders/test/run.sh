#!/bin/bash
# Run the built d3d8.dll outside the game: probe_test.exe draws a shadow silhouette, a lit
# textured wall and a bullet-hole decal for 320 frames through it, under 32-bit Wine with a
# virtual display and software OpenGL. Checks that the DLL loads, the probes run and log, and
# the decal rule compiles and draws decal_parallax.hlsl; saves frame_parallax.bmp (rule on)
# and frame_flat.bmp (off) to compare. Then the same for post-processing (frame_post.bmp) and
# a lightmapped brick wall with the surface= rule (frame_wall.bmp, off: frame_wallflat.bmp),
# and that wall with its lightmap swapped by replace= (frame_wallgi.bmp); then a lit sphere
# without and with charlight=1 (frame_sphere.bmp, frame_spherelit.bmp); last the wall with
# lmcapture=1 (U2Shaders/capture/: what tools/python/U2Blender/bake_lightmaps.py bakes from;
# with a bake in U2Shaders/baked/, "wine probe_test.exe wallbaked" shows it in place). Wine's d3d9 is not dgVoodoo: the depth probe results
# here say nothing about the real game setup.
#
# Needs: ../build-mingw.sh run first, g++-mingw-w64-i686, wine32:i386, xvfb, and the x86
# d3dcompiler_47.dll that ../hlslcheck.sh fetches (FXC_DIR, default ~/.cache/u2shaders-fxc).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
FXC_DIR=${FXC_DIR:-$HOME/.cache/u2shaders-fxc}
RUN=$HERE/../build/test

[ -f "$HERE/../build/d3d8.dll" ] || { echo "run ../build-mingw.sh first"; exit 2; }
[ -f "$FXC_DIR/x86/d3dcompiler_47.dll" ] || { echo "run ../hlslcheck.sh once (fetches d3dcompiler_47)"; exit 2; }
rm -rf "$RUN"
mkdir -p "$RUN/U2Shaders"
i686-w64-mingw32-g++ -O1 -std=c++17 -o "$RUN/probe_test.exe" "$HERE/probe_test.cpp" -ld3d8 -lgdi32 -static -static-libgcc -static-libstdc++
cp "$HERE/../build/d3d8.dll" "$FXC_DIR/x86/d3dcompiler_47.dll" "$RUN/"
cp "$HERE"/../shaders/*.hlsl "$RUN/U2Shaders/"

export WINEPREFIX=${WINEPREFIX:-$HERE/../build/wineprefix} WINEARCH=win32 WINEDEBUG=-all
export WINEDLLOVERRIDES="d3d8=n;d3dcompiler_47=n;mscoree,mshtml="
cd "$RUN"
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe flat
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe
echo "== U2Shaders.log"; cat U2Shaders.log
echo "== chars.txt"; cat U2Shaders/dump/chars.txt
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe post
echo "== U2Shaders.log (post)"; cat U2Shaders.log
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe wallflat
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe wall
echo "== U2Shaders.log (wall)"; cat U2Shaders.log
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe wallgi
echo "== U2Shaders.log (wallgi)"; cat U2Shaders.log
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe sphere
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe spherelit
echo "== U2Shaders.log (spherelit)"; cat U2Shaders.log
xvfb-run -a -s "-screen 0 1024x768x24" wine probe_test.exe wallcap
echo "== U2Shaders.log (wallcap)"; cat U2Shaders.log
echo "== capture"; cat U2Shaders/capture/lightmaps.txt
echo "frames: $RUN/frame_flat.bmp $RUN/frame_parallax.bmp $RUN/frame_post.bmp $RUN/frame_wallflat.bmp $RUN/frame_wall.bmp $RUN/frame_wallgi.bmp $RUN/frame_sphere.bmp $RUN/frame_spherelit.bmp"

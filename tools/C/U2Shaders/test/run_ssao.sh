#!/bin/bash
# SSAO under Wine: ssao_test.exe draws a room (floor, three walls, a step, a crate; flat
# colours, no lighting) through a d3d8.dll built from the fork's 'ssao' branch, with post=1,
# and saves frame_ssao_off.bmp, frame_ssao_on.bmp and frame_ssao_debug.bmp (the AO alone).
# Usage: run_ssao.sh path/to/d3d8.dll path/to/fork/shaders
# Needs g++-mingw-w64-i686, wine32, xvfb and the x86 d3dcompiler_47.dll (../hlslcheck.sh).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DLL=${1:?d3d8.dll}; SHADERS=${2:?shaders folder}
FXC_DIR=${FXC_DIR:-$HOME/.cache/u2shaders-fxc}
RUN=$HERE/../build/ssaotest
rm -rf "$RUN"; mkdir -p "$RUN/U2Shaders"
i686-w64-mingw32-g++ -O1 -std=c++17 -o "$RUN/ssao_test.exe" "$HERE/ssao_test.cpp" -ld3d8 -lgdi32 -static -static-libgcc -static-libstdc++
cp "$DLL" "$FXC_DIR/x86/d3dcompiler_47.dll" "$RUN/"
cp "$SHADERS"/*.hlsl "$RUN/U2Shaders/"
export WINEPREFIX=${WINEPREFIX:-$HERE/../build/wineprefix} WINEARCH=win32 WINEDEBUG=-all
export WINEDLLOVERRIDES="d3d8=n;d3dcompiler_47=n;mscoree,mshtml="
cd "$RUN"
for m in off on debug; do xvfb-run -a -s "-screen 0 1024x768x24" wine ssao_test.exe $m; done
grep -i "ssao" U2Shaders.log

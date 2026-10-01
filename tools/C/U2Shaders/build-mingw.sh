#!/bin/bash
# Build d3d8.dll (Win32, Release) from d3d8to9 + this folder's patch with MinGW: no Visual
# Studio needed. Needs git and g++-mingw-w64-i686 (Linux) or an i686 MinGW toolchain.
# Output: build/d3d8.dll (standalone: the C++ runtime is linked in statically).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=255338f                     # the d3d8to9 commit the patch applies to
OUT=$HERE/build
SRC=$OUT/d3d8to9

rm -rf "$SRC"
mkdir -p "$OUT"
git clone -q https://github.com/crosire/d3d8to9.git "$SRC"
cd "$SRC"
git checkout -q $BASE
git -c user.name=build -c user.email=build@localhost am -q "$HERE"/0001-*.patch

i686-w64-mingw32-windres -I res -I source res/d3d8to9.rc -O coff -o "$OUT/res.o"
# -fno-strict-aliasing: d3d8to9 type-puns pointers, which MSVC tolerates and GCC's optimiser may not
i686-w64-mingw32-g++ -std=c++17 -O2 -fno-strict-aliasing -DNDEBUG -DD3D8TO9NOLOG -fms-extensions \
	-Wall -Wno-delete-non-virtual-dtor -Wno-unknown-pragmas -Wno-format -I source \
	-shared -o "$OUT/d3d8.dll" source/*.cpp "$OUT/res.o" res/d3d8.def \
	-Wl,--enable-stdcall-fixup -static -static-libgcc -static-libstdc++ \
	-ld3d9 -ld3dcompiler_47 -lgdi32
i686-w64-mingw32-strip "$OUT/d3d8.dll"
rm -f "$OUT/res.o"
echo "built $OUT/d3d8.dll"

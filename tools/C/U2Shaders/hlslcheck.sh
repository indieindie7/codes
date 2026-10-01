#!/bin/bash
# Compile-check U2Shaders HLSL exactly as u2shaders.hpp does at runtime:
# Microsoft's d3dcompiler_47, entry "main", ps_2_a first, then ps_2_b.
# Reports the profile that took and the instruction / register budget used.
#
# Usage: ./hlslcheck.sh [file.hlsl ...]      (default: shaders/*.hlsl)
#
# Needs fxc.exe + d3dcompiler_47.dll, fetched once from Microsoft's Windows SDK
# NuGet package into $FXC_DIR (default ~/.cache/u2shaders-fxc). On Linux they
# run under Wine (apt install wine64); in Git Bash / MSYS they run natively.
set -u

SDK_VER=10.0.28000.2705
FXC_DIR=${FXC_DIR:-$HOME/.cache/u2shaders-fxc}
HERE=$(cd "$(dirname "$0")" && pwd)

case "$(uname -s)" in
	MINGW*|MSYS*|CYGWIN*) NATIVE=1 ;;
	*) NATIVE= ;;
esac

if [ ! -f "$FXC_DIR/fxc.exe" ] || [ ! -f "$FXC_DIR/d3dcompiler_47.dll" ]; then
	echo "Fetching fxc + d3dcompiler_47 (Windows SDK $SDK_VER, ~160 MB, once)..."
	mkdir -p "$FXC_DIR"
	pkg="$FXC_DIR/sdk.nupkg"
	curl -fsSL -o "$pkg" "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.cpp/$SDK_VER/microsoft.windows.sdk.cpp.$SDK_VER.nupkg" || { echo "download failed"; exit 2; }
	python3 - "$pkg" "$FXC_DIR" "$SDK_VER" <<'EOF' || { echo "extract failed"; exit 2; }
import sys, zipfile
pkg, out, ver = sys.argv[1:4]
base = "c/bin/%s.0/x64/" % ver.rsplit(".", 1)[0]
with zipfile.ZipFile(pkg) as z:
    for name in ("fxc.exe", "d3dcompiler_47.dll"):
        with open("%s/%s" % (out, name), "wb") as f:
            f.write(z.read(base + name))
EOF
	rm -f "$pkg"
fi

if [ -n "$NATIVE" ]; then
	fxc() { "$FXC_DIR/fxc.exe" "$@"; }
	winpath() { cygpath -w "$1"; }
else
	command -v wine >/dev/null || { echo "wine not found (apt install wine64)"; exit 2; }
	export WINEPREFIX=${WINEPREFIX:-$FXC_DIR/wineprefix} WINEDEBUG=-all
	fxc() { wine "$FXC_DIR/fxc.exe" "$@"; }
	winpath() { echo "Z:$1" | tr '/' '\\'; }
fi

[ $# -eq 0 ] && set -- "$HERE"/shaders/*.hlsl
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
status=0

for f in "$@"; do
	name=$(basename "$f" .hlsl)
	dir=$(cd "$(dirname "$f")" && pwd)
	ok=
	for prof in ps_2_a ps_2_b; do
		asm="$tmp/${name}_$prof.asm"
		out=$(cd "$dir" && fxc /nologo /T $prof /E main /Fc "$(winpath "$asm")" "$name.hlsl" 2>&1 | tr -d '\r')
		if [ -s "$asm" ]; then
			slots=$(grep -m1 -oE 'approximately [0-9]+' "$asm" | grep -oE '[0-9]+')
			temps=$(grep -oE '\br[0-9]+\b' "$asm" | tr -d r | sort -n | tail -1)
			consts=$(grep -oE '\bc[0-9]+\b' "$asm" | sort -u | wc -l)
			maxtemps=32
			[ $prof = ps_2_a ] && maxtemps=22
			printf 'OK    %-12s %s  slots %s/512  temps %s/%s  constants %s/32\n' \
				"$name" "$prof" "${slots:-?}" "$(( ${temps:--1} + 1 ))" $maxtemps "$consts"
			grep -i 'warning' <<<"$out" | sed 's#^.*[\\/]##' | sort -u | sed 's#^#      #'
			ok=1
			break
		fi
		echo "FAIL  $name  $prof"
		grep -E 'error' <<<"$out" | sed 's#^.*[\\/]##' | sed -E 's/\([0-9,-]+\)//' | sort -u | head -4 | sed 's#^#      #'
	done
	[ -z "$ok" ] && status=1
done
exit $status

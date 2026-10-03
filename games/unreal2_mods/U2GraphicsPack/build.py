# Builds U2GraphicsPack-<ver>-nexus.zip (no installer) from the files installed in the user's game.
import os, zipfile
VER = "1.0"
G = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System"
FORK = r"C:\Users\john\Documents\github\d3d8to9"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.expanduser("~"), "Downloads", "U2GraphicsPack-%s-nexus.zip" % VER)
TOP = "U2GraphicsPack-%s/" % VER
SHADERS = ["core.hlsl", "pcss_map.hlsl", "pcss_proj.hlsl", "post_bright.hlsl", "post_blur.hlsl",
           "post_down.hlsl", "post_up.hlsl", "post_final.hlsl", "smaa_passes.hlsl", "SMAA.hlsl",
           "AreaTexDX9.dds", "SearchTex.dds", "lut_u2.bmp", "lut_neutral.bmp", "SMAA-LICENSE.txt"]
def text(path):
    return open(path, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(TOP + "README.txt", text(os.path.join(HERE, "README.txt")))
    z.writestr(TOP + "LICENSES/d3d8to9.txt", text(os.path.join(FORK, "LICENSE.md")))
    z.write(os.path.join(FORK, r"bin\Release\d3d8.dll"), TOP + "System/d3d8.dll")
    z.writestr(TOP + "System/U2Shaders.ini", text(os.path.join(HERE, "U2Shaders.ini")))
    z.write(os.path.join(G, "U2SoftShadows.u"), TOP + "System/U2SoftShadows.u")
    for f in SHADERS:
        p = os.path.join(G, "U2Shaders", f)
        if f.endswith((".hlsl", ".txt")):
            z.writestr(TOP + "System/U2Shaders/" + f, text(p))
        else:
            z.write(p, TOP + "System/U2Shaders/" + f)
    for i in z.infolist():
        print("%9d  %s" % (i.file_size, i.filename))
print(OUT, os.path.getsize(OUT))

U2Shaders - custom pixel shaders for Unreal II (installed 2026-09-30)

Stack: Unreal2.exe -> d3d8.dll (d3d8to9 fork with U2Shaders, source in
Documents\github\d3d8to9) -> d3d9.dll (dgVoodoo 2.87.5) -> Direct3D 11.
dgVoodoo.conf still applies.

Settings: System\U2Shaders.ini   (shader=<texture hash> <file in this folder>)
Log:      System\U2Shaders.log

To go back to the old setup: copy d3d8.dll.dgvoodoo-keep over d3d8.dll and
delete d3d9.dll.

"""Writes test/sample.t3d: a small map in UnrealEd 2's T3D layout (a room carved by a subtract
brush, a rotated, scaled add brush inside it, a light, a static mesh, a player start and a
trigger). The cube's -X face is UnrealEd's default cube face; the other faces follow the same
rule (normal = (v1 - v0) x (v2 - v0), pointing out of the brush)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import t3d

def cube(h, tex):
    faces = []
    for axis in range(3):
        for sign in (-1, 1):
            n = [0, 0, 0]; n[axis] = sign
            # two in-plane axes, ordered so (v1-v0)x(v2-v0) points along n
            a, b = (axis + 1) % 3, (axis + 2) % 3
            corners = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
            verts = []
            for ca, cb in corners:
                v = [0, 0, 0]; v[axis] = sign * h; v[a] = ca * h; v[b] = cb * h
                verts.append(tuple(v))
            # pick the order whose normal matches n
            p = t3d.Poly(); p.verts = verts
            nn = t3d.cross(t3d.sub(verts[1], verts[0]), t3d.sub(verts[2], verts[0]))
            if t3d.dot(nn, n) < 0:
                verts = [verts[0]] + verts[1:][::-1]
            p.verts = verts
            p.header = {'Texture': tex, 'Flags': '0'}
            p.origin = verts[0]
            p.normal = tuple(float(c) for c in n)
            # texture axes in the plane
            u = [0, 0, 0]; u[a if axis != 2 else 0] = 1
            v = [0, 0, 0]; v[b if axis != 2 else 1] = -1 if axis != 2 else 1
            if axis == 0:
                u, v = (0, 1, 0), (0, 0, -1)
            elif axis == 1:
                u, v = (1, 0, 0), (0, 0, -1)
            p.texture_u = tuple(float(c) for c in u)
            p.texture_v = tuple(float(c) for c in v)
            faces.append(p)
    return faces

def brush(name, model, csg, faces, extra):
    lines = ['Begin Actor Class=Brush Name=%s' % name, '    Begin Brush Name=%s' % model, '       Begin PolyList']
    for p in faces:
        lines += p.to_lines('          ')
    lines += ['       End PolyList', '    End Brush', "    Brush=Model'myLevel.%s'" % model]
    if csg:
        lines.append('    CsgOper=%s' % csg)
    lines += ['    ' + e for e in extra]
    lines += ['    Name="%s"' % name, 'End Actor']
    return lines

lines = ['Begin Map',
         'Begin Actor Class=LevelInfo Name=LevelInfo0', '    Title="Sample"', '    Name="LevelInfo0"', 'End Actor']
lines += brush('Brush0', 'Model0', None, cube(128, 'Engine.DefaultTexture'), ['Location=(X=0,Y=0,Z=0)'])
lines += brush('Brush1', 'Model1', 'CSG_Subtract', cube(512, 'Walls.Brick01'),
               ['Location=(X=0,Y=0,Z=256)', 'PolyFlags=0'])
lines += brush('Brush2', 'Model2', 'CSG_Add', cube(64, 'Metal.Panel02'),
               ['Location=(X=200,Y=-150,Z=64)', 'Rotation=(Yaw=8192)',
                'PostScale=(Scale=(X=1.000000,Y=1.000000,Z=2.000000),SheerAxis=SHEER_ZX)',
                'PrePivot=(X=0,Y=0,Z=-64)'])
lines += ['Begin Actor Class=Light Name=Light0', '    LightBrightness=128.000000', '    LightHue=30',
          '    LightSaturation=200', '    LightRadius=32.000000', '    Location=(X=-100,Y=200,Z=600)',
          '    Name="Light0"', 'End Actor']
lines += ['Begin Actor Class=StaticMeshActor Name=StaticMeshActor0',
          "    StaticMesh=StaticMesh'Crates.Wood.Crate01'", '    Location=(X=-300,Y=-300,Z=32)',
          '    Rotation=(Pitch=0,Yaw=16384,Roll=0)', '    DrawScale=1.500000',
          '    DrawScale3D=(X=1.000000,Y=2.000000,Z=1.000000)', '    Name="StaticMeshActor0"', 'End Actor']
lines += ['Begin Actor Class=PlayerStart Name=PlayerStart0', '    Location=(X=0,Y=0,Z=60)',
          '    Rotation=(Yaw=-16384)', '    Name="PlayerStart0"', 'End Actor']
lines += ['Begin Actor Class=Trigger Name=Trigger0', '    Event=OpenDoor', '    CollisionRadius=80.000000',
          '    Location=(X=300,Y=100,Z=40)', '    Name="Trigger0"', 'End Actor']
lines += ['End Map']
out = os.path.join(os.path.dirname(__file__), 'sample.t3d')
with open(out, 'w', newline='\r\n') as f:
    f.write('\n'.join(lines) + '\n')
print('wrote', out)

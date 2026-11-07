"""build_smpl_mesh: NLF's torchscript ships the SMPL template verts but no faces -> rebuild a triangle list.
Ball pivoting (pymeshlab, radii 1/2/4 x median vertex spacing) on v_template, manifold repair, hole close,
coherent winding (outward). Writes smpl_mesh.npz: faces over split verts + vmap (split vert -> SMPL vert index).
Usage: py -3.13 build_smpl_mesh.py   (env NLF_MODEL = torchscript path)"""
import os, numpy as np, torch, torchvision, pymeshlab as ml, trimesh
from scipy.spatial import cKDTree
NLF = os.environ.get('NLF_MODEL', r'C:\Users\john\Documents\DeadOrAlive\saturn\sonar_intro\models_pose3d\nlf_l_multi_0.3.2.torchscript')
V = torch.jit.load(NLF, map_location='cpu').body_models.smpl.v_template.numpy().astype(np.float64)
d, _ = cKDTree(V).query(V, k=2); r = np.median(d[:, 1])
ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(V)); ms.compute_normal_for_point_clouds(k=12)
for f in (1, 2, 4): ms.generate_surface_reconstruction_ball_pivoting(ballradius=ml.PureValue(r * f))
for _ in range(3):
    ms.meshing_remove_duplicate_faces(); ms.meshing_repair_non_manifold_edges(method=0); ms.meshing_repair_non_manifold_vertices()
ms.meshing_remove_unreferenced_vertices()
for hs in (30, 100, 400): ms.meshing_close_holes(maxholesize=hs, newfaceselected=False, selfintersection=False)
ms.meshing_re_orient_faces_coherently()
c = ms.current_mesh(); Vo, Fo = c.vertex_matrix(), c.face_matrix()
dist, vmap = cKDTree(V).query(Vo); assert dist.max() < 1e-9
t = trimesh.Trimesh(Vo, Fo, process=False)
if t.volume < 0: Fo = Fo[:, ::-1].copy(); t = trimesh.Trimesh(Vo, Fo, process=False)
print('verts', len(Vo), 'faces', len(Fo), 'watertight', t.is_watertight, 'winding', t.is_winding_consistent)
np.savez(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smpl_mesh.npz'), faces=Fo.astype(np.int32), vmap=vmap.astype(np.int32))

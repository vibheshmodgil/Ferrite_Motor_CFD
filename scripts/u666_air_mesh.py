"""U666 external-air mesh from the SIMPLIFIED housing envelope -> mesh/u666/u666_air_s.msh (patches motor / ambient).
Run: .venv/Scripts/python -I scripts/u666_air_mesh.py   (mm; env S_FIN S_SKIN S_FAR; --geo-only counts faces only)
Obstacle = housing parts + cavity fillers (housing_simple.fills) + fin-root fill (r<R_ROOT, 0.2 mm slots) + shaft stub.
ponytail: motor shown suspended (no feet / mounting plate); box walls at ambient."""
import gmsh, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import u666_housing_simple as hs
S_FIN, S_SKIN, S_FAR = [float(os.environ.get(k, d)) for k, d in (("S_FIN", 1.6), ("S_SKIN", 3.5), ("S_FAR", 45))]
R_ROOT, STUB = 80.2, (10.0, 120.0, 148.85)          # fin-root fill radius; shaft stub r, z0, z1
BOX = (-330, 330, -330, 520, -330, 420)             # x0 x1 y0 y1 z0 z1 (y up)
hs.K['BOX'] = (*hs.K['BOX'][:5], -83.7)   # box rim flush with the cover end (0.1 mm step -> sliver cells)
hs.K['BOSS_DZ'] = 0.0   # boss base flush with the front wall (0.2 mm step -> sliver cells)
parts = hs.build(); o = hs.o; M = gmsh.model
F = hs.fills()
z0 = hs.K['FIN_C0'] - 5; z1 = hs.K['FIN_C0'] + hs.K['FIN_PITCH'] * (hs.K['FIN_N'] - 1) + 5
root = o.addCylinder(0, 0, z0, 0, 0, z1 - z0, R_ROOT)
stub = o.addCylinder(0, 0, STUB[1], 0, 0, STUB[2] - STUB[1], STUB[0])
o.synchronize()
obs, _ = o.fuse([(3, t) for v in parts.values() for t in v], [(3, t) for t in F] + [(3, root), (3, stub)]); o.synchronize()
print("obstacle volumes", len(obs), "vol cm3", sum(o.getMass(*e) for e in obs) / 1e3, flush=True)
bx = o.addBox(BOX[0], BOX[2], BOX[4], BOX[1] - BOX[0], BOX[3] - BOX[2], BOX[5] - BOX[4])
air, _ = o.cut([(3, bx)], obs, removeTool=True); o.synchronize()
amb, mot = [], []
for _, f in M.getBoundary(air, oriented=False):
    b = M.getBoundingBox(2, f)
    on = any(abs(b[i] - BOX[2 * i]) < 1e-3 and abs(b[i + 3] - BOX[2 * i]) < 1e-3 or abs(b[i] - BOX[2 * i + 1]) < 1e-3 and abs(b[i + 3] - BOX[2 * i + 1]) < 1e-3 for i in range(3))
    (amb if on else mot).append(f)
M.addPhysicalGroup(2, amb, name="ambient"); M.addPhysicalGroup(2, mot, name="motor"); M.addPhysicalGroup(3, [t for _, t in air], name="air")
print("faces ambient", len(amb), "motor", len(mot), flush=True)
if "--geo-only" in sys.argv: sys.exit()
fd = M.mesh.field
fd.add("Distance", 1); fd.setNumbers(1, "SurfacesList", mot); fd.setNumber(1, "Sampling", 40)
fd.add("Threshold", 2); fd.setNumber(2, "InField", 1); fd.setNumber(2, "SizeMin", S_SKIN); fd.setNumber(2, "SizeMax", S_FAR)
fd.setNumber(2, "DistMin", 4); fd.setNumber(2, "DistMax", 220)
fd.add("Box", 3); [fd.setNumber(3, k, v) for k, v in (("VIn", S_FIN), ("VOut", S_FAR), ("XMin", -96), ("XMax", 96), ("YMin", -96), ("YMax", 96), ("ZMin", z0 - 3), ("ZMax", z1 + 3), ("Thickness", 25))]
fd.add("Min", 4); fd.setNumbers(4, "FieldsList", [2, 3]); fd.setAsBackgroundMesh(4)
for k, v in (("Mesh.MeshSizeFromPoints", 0), ("Mesh.MeshSizeFromCurvature", 0), ("Mesh.MeshSizeExtendFromBoundary", 0), ("Mesh.Algorithm3D", float(os.environ.get("ALG3", 1))), ("Mesh.Optimize", 1), ("Mesh.OptimizeNetgen", 1)):
    gmsh.option.setNumber(k, v)
gmsh.option.setNumber("General.NumThreads", 4)
try: M.mesh.generate(3)
except Exception as e:
    import re; print("FAIL", e); [print(t, M.getType(2, t), [round(x, 1) for x in M.getBoundingBox(2, t)], o.getMass(2, t)) for t in map(int, re.findall(r"surface (\d+)", str(e))[:1])]; raise
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.write(os.environ.get("OUTM", "mesh/u666/u666_air_s.msh"))
print("nodes", len(M.mesh.getNodes()[0]), "tets", sum(len(e) for e in M.mesh.getElementsByType(4)[:1]), flush=True)

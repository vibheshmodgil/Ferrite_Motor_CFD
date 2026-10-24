"""Thermal model of motor_65 for OpenFOAM: CAD parts -> conformal multi-region tet mesh (gmsh, mm).

    .venv/Scripts/python -I scripts/build_mesh.py [--solids-only] [--size 3]

Regions (physical volumes): housing (housing + rear cover, AlSi10Mg), stator (12 tooth segments), winding
(homogenised Cu + resin + bobbin, 12 blocks), rotor (lamination stack), magnets (20 ferrite blocks), shaft,
bearings, seal, inair (air inside the motor, effective conductivity), air (outside, natural-convection CFD).
Writes mesh/motor.msh (v2.2) and mesh/regions.json (volumes, for heat capacities and loss densities).
"""
import gmsh, json, math, os, sys
import numpy as np

CAD = os.environ.get("CAD", r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65")   # CAD=/mnt/c/... in WSL
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh")
SOLIDS_ONLY = "--solids-only" in sys.argv
AIR_ONLY = "--air-only" in sys.argv        # outside air only, for the natural-convection CFD (patches motor/ambient)
H = float(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 3.0   # base solid cell size, mm

# winding block in the tooth frame (tooth axis +y): racetrack around the neck, clipped to the 30 deg slot wedge
W_X, W_Y, W_Z = 17.3, (55.0, 72.0), 42.0      # from the coil STEP: |x|<=17.3, y 54.6..70.2, end turns to |z|~42
R_BORE = 53.5                                 # stator bore; rotor (OD 106) is grown to it, the 0.5 mm gap is a
                                              # thermal resistance on the rotor/stator interface (thicknessLayers)
ROTOR_Z = 33.0
CAV_R, CAV_Z = 84.0, (-50.0, 77.0)
BOX = (-300, 300, -300, 500, -350, 300)       # outside air, mm; gravity -y, so more room above for the plume

occ = gmsh.model.occ
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 1)
for o in ("OCCFixDegenerated", "OCCFixSmallEdges", "OCCFixSmallFaces"):
    gmsh.option.setNumber("Geometry." + o, 1)
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-3)      # mm; glues parts that touch to within 1 um
inst = json.load(open(os.path.join(CAD, "instances.json")))["instances"]


def load(part):
    out = occ.importShapes(os.path.join(CAD, part + ".step"))
    return [t for d, t in out if d == 3]


def place(part, keep=None):
    """Every instance of `part`, moved into the assembly frame."""
    tags, base = [], load(part)
    for i in inst:
        if i["part"] != part:
            continue
        cp = occ.copy([(3, t) for t in base])
        R, t = np.array(i["R"]), i["t"]
        occ.affineTransform(cp, list(np.hstack([R, np.array(t)[:, None]]).ravel()))
        tags += [c[1] for c in cp]
    occ.remove([(3, t) for t in base], recursive=True)
    return tags


groups = {}
# housing + rear cover + a ring where the cover O-ring sits (the 1 mm groove gap r 81-82, z 71-75 is too thin to mesh)
oring = occ.cut([(3, occ.addCylinder(0, 0, 70.5, 0, 0, 5, 82.5))], [(3, occ.addCylinder(0, 0, 69, 0, 0, 8, 80.0))])[0]
HOUSING = os.environ.get("HOUSING_STEP")   # fin variants (make_housing_fins.py); default the CAD housing
hs, _ = occ.fuse([(3, t) for d, t in occ.importShapes(HOUSING) if d == 3] if HOUSING else [(3, t) for t in load("housing")], [(3, t) for t in load("rear_cover")] + oring)
groups["housing"] = [t for _, t in hs]
groups["shaft"] = load("shaft")
# ponytail: bearings as plain 52/30 x 15 steel rings (the STEP's B-spline shield faces don't mesh cleanly)
groups["bearings"] = []
for i in inst:
    if i["part"] == "bearing_52x30x15":
        z0 = i["t"][2] + (min(0, 15 * i["R"][2][2]))          # ring spans t_z .. t_z + 15 R_zz
        o = occ.addCylinder(0, 0, z0, 0, 0, 15, 26.0)
        h = occ.addCylinder(0, 0, z0 - 1, 0, 0, 17, 15.0)
        groups["bearings"] += [t for _, t in occ.cut([(3, o)], [(3, h)])[0]]
groups["magnets"] = place("magnet_ferrite")
teeth = place("tooth_65")
occ.synchronize()

# stator core: the 12 segments fused (butt joints are in contact)
st, _ = occ.fuse([(3, teeth[0])], [(3, t) for t in teeth[1:]])
groups["stator"] = [t for _, t in st]

# windings: block - neck hole, clipped to the slot wedge, minus the tooth (block then hugs neck, shoe and yoke)
win = []
for k in range(12):
    blk = occ.addBox(-W_X, W_Y[0], -W_Z, 2 * W_X, W_Y[1] - W_Y[0], 2 * W_Z)
    hole = occ.addBox(-7.0, 50, -32.3, 14.0, 30, 64.6)               # inside the neck (tooth fills it)
    a = math.radians(15)
    wedge = occ.addCylinder(0, 0, -60, 0, 0, 120, 100, angle=2 * a)
    occ.rotate([(3, wedge)], 0, 0, 0, 0, 0, 1, math.pi / 2 - a)      # wedge centred on +y
    w, _ = occ.cut([(3, blk)], [(3, hole)])
    w, _ = occ.intersect(w, [(3, wedge)])
    win += w
# each tooth instance points its local +y along R[:,1]; the blocks were built on +y
angs = sorted({round(math.degrees(math.atan2(i["R"][1][1], i["R"][0][1])), 3) for i in inst if i["part"] == "tooth_65"})
for (d, t), ang in zip(win, angs):
    occ.rotate([(d, t)], 0, 0, 0, 0, 0, 1, math.radians(ang - 90))
w, _ = occ.cut(win, [(3, t) for t in groups["stator"]], removeTool=False)
groups["winding"] = [t for _, t in w]

# rotor core: OD grown to the bore, minus magnets (conformal pockets, glue gap absorbed) and the shaft bore
rc = occ.addCylinder(0, 0, -ROTOR_Z, 0, 0, 2 * ROTOR_Z, R_BORE)
bore = occ.addCylinder(0, 0, -ROTOR_Z - 1, 0, 0, 2 * ROTOR_Z + 2, 15.0)
r, _ = occ.cut([(3, rc)], [(3, bore)] + [(3, t) for t in groups["magnets"]], removeTool=False)
occ.remove([(3, bore)])
groups["rotor"] = [t for _, t in r]
occ.synchronize()
def check(stage):
    live = {t for _, t in gmsh.model.getEntities(3)}
    flat = [t for g in groups.values() for t in g]
    dup = {t for t in flat if flat.count(t) > 1}
    stray = live - set(flat) - ({box} if "box" in globals() else set())
    print(stage, {n: len(g) for n, g in groups.items()}, "dup", dup, "dead", set(flat) - live, "stray", stray)
    assert not dup and set(flat) <= live, stage
check("parts")
# ponytail: shaft seal and cable glands left out (a few grams of rubber/plastic); the cavity below closes the motor

# air inside the motor: a cylinder that ends inside the housing walls (side wall r 80-86, front wall z -52..-48,
# rear cover plate z 76..78; sampled from the CAD), minus every part. The cut makes it a closed region, so the
# glands' holes and the O-ring groove cannot connect it to the outside air.
cav = occ.addCylinder(0, 0, CAV_Z[0], 0, 0, CAV_Z[1] - CAV_Z[0], CAV_R)
c, _ = occ.cut([(3, cav)], [(3, t) for g in groups.values() for t in g], removeTool=False)
groups["inair"] = [t for _, t in c]
occ.synchronize()

check("with cavity")
# everything + a box -> conformal fragments; the air pieces are whatever no part claims
allparts = [(3, t) for g in groups.values() for t in g]
box = occ.addBox(BOX[0], BOX[2], BOX[4], BOX[1] - BOX[0], BOX[3] - BOX[2], BOX[5] - BOX[4])
out, omap = occ.fragment([(3, box)], allparts)
occ.synchronize()

owner = {}
for (d, t), children in zip([(3, box)] + allparts, omap):
    for c in children:
        if (d, t) == (3, box):
            owner.setdefault(c[1], "air?")
        else:
            name = next(n for n, g in groups.items() if t in g)
            owner[c[1]] = name            # a part claim beats the box claim
regions = {n: [] for n in groups}
regions["air"] = []
for t, n in owner.items():
    regions["air" if n == "air?" else n].append(t)
print("outside air pieces:", len(regions["air"]))   # >1 = pockets (shaft bore, seal gap): still outside air
if SOLIDS_ONLY:
    occ.remove([(3, t) for t in regions.pop("air")], recursive=True)
    occ.synchronize()

def split_skin(air):
    """Boundary faces of the air volume -> (box faces, motor faces)."""
    amb, mot = [], []
    for _, f in gmsh.model.getBoundary([(3, t) for t in air], oriented=False):
        x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(2, abs(f))
        on_box = any(abs(a - b) < 1e-3 and abs(c - b) < 1e-3 for a, c, b in
                     ((x0, x1, BOX[0]), (x0, x1, BOX[1]), (y0, y1, BOX[2]), (y0, y1, BOX[3]), (z0, z1, BOX[4]), (z0, z1, BOX[5])))
        (amb if on_box else mot).append(abs(f))
    return amb, mot


if AIR_ONLY:
    occ.remove([(3, t) for n, ts in regions.items() if n != "air" for t in ts], recursive=True)
    occ.synchronize()
    regions = {"air": regions["air"]}
    amb, mot = split_skin(regions["air"])
    gmsh.model.addPhysicalGroup(2, amb, name="ambient")
    gmsh.model.addPhysicalGroup(2, mot, name="motor")
    print("air-only: ambient faces", len(amb), "motor faces", len(mot))

info = {}
for n, ts in regions.items():
    if not ts:
        continue
    gmsh.model.addPhysicalGroup(3, ts, name=n)
    info[n] = sum(occ.getMass(3, t) for t in ts) * 1e-9          # m3
    print(f"{n:10s} pieces {len(ts):3d}  volume {info[n]*1e6:9.1f} cm3")

if "--geo-only" in sys.argv:
    sys.exit(0)

# mesh size: H in the solids, fine at the motor skin in the air, coarse far away
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.6)
gmsh.option.setNumber("Mesh.MeshSizeMax", 40.0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
fields = []
solid_vols = [t for n, ts in regions.items() if n != "air" for t in ts]
if solid_vols:
    f_in = gmsh.model.mesh.field.add("Constant")
    gmsh.model.mesh.field.setNumbers(f_in, "VolumesList", solid_vols)
    gmsh.model.mesh.field.setNumber(f_in, "VIn", H)
    gmsh.model.mesh.field.setNumber(f_in, "VOut", 1e9)
    fields.append(f_in)
if regions.get("air"):
    skin = split_skin(regions["air"])[1]
    dist = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", skin)
    th = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(th, "InField", dist)
    for k, v in dict(SizeMin=float(os.environ.get("AIR_SKIN", H)), SizeMax=40.0, DistMin=4.0, DistMax=250.0).items():
        gmsh.model.mesh.field.setNumber(th, k, v)
    fields.append(th)
fmin = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(fmin, "FieldsList", fields)
gmsh.model.mesh.field.setAsBackgroundMesh(fmin)
gmsh.option.setNumber("Mesh.Algorithm", 6)
gmsh.option.setNumber("Mesh.Algorithm3D", 10)       # HXT, multithreaded
gmsh.option.setNumber("General.NumThreads", int(os.environ.get("NTHREADS", 8)))
gmsh.option.setNumber("Mesh.Optimize", 1)
try:
    gmsh.model.mesh.generate(3)
except Exception as e:
    bad = [t for d, t in gmsh.model.getEntities(2) if len(gmsh.model.mesh.getElements(2, t)[1]) == 0]
    print("FAILED:", e, "- surfaces without mesh:", bad[:20])
    for t in bad[:5]:
        print(t, gmsh.model.getBoundingBox(2, t), gmsh.model.getAdjacencies(2, t)[0])
    raise
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.SaveAll", 0)
os.makedirs(OUT, exist_ok=True)
name = ("motor_solids" if SOLIDS_ONLY else "air" if AIR_ONLY else "motor") + os.environ.get("MESH_TAG", "")
gmsh.write(os.path.join(OUT, name + ".msh"))
_, et, _ = gmsh.model.mesh.getElements(3)
info["_cells"] = int(sum(len(e) for e in et))
json.dump(info, open(os.path.join(OUT, name + "_regions.json"), "w"), indent=1)
print("tets:", info["_cells"])

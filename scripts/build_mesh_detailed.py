"""Detailed thermal model of motor_65: real coils, bobbins, impregnation resin and busbars -> conformal tet mesh.

    .venv/Scripts/python -I scripts/build_mesh_detailed.py [--geo-only] [--wire 0.9]

Regions: housing, stator, coil (12 real swept Cu wires incl. leads), bobbin (12 PA66-GF30, simplified), resin (impregnation
filling the winding space between wire, bobbin and tooth), busbar (3 net plates), strap (6 link straps), tbar (3
terminal bars), rotor, magnets, shaft, bearings, inair. Writes mesh/motor_detailed.msh + _regions.json (mm).
"""
import gmsh, json, math, os, sys, time
import numpy as np

CAD = os.environ.get("CAD", r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65")
OUT = os.environ.get("OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh"))
H = 3.0                                                     # base cell size, mm
HW = float(sys.argv[sys.argv.index("--wire") + 1]) if "--wire" in sys.argv else 0.9   # coil / resin / bobbin
HB = 1.5                                                    # busbar, straps, terminal bars
# resin envelope in the tooth frame: around the real coil (|x| <= 17.5, y 54.6..70.2, end turns to |z| 44.97),
# under the link straps (z 45.75) -> z +-45.5; clipped to the 30 deg slot wedge; tooth, bobbins, wire cut out
E_X, E_Y, E_Z = 18.0, (53.8, 72.0), 45.5      # y 53.8: the end turns reach y 54.10 (54.3 shaved a 0.2 mm cap off the wire)
R_BORE, ROTOR_Z = 53.5, 33.0
CAV_R, CAV_Z = 84.0, (-50.0, 77.0)

occ = gmsh.model.occ
T0 = time.time()
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 1)
for o in ("OCCFixDegenerated", "OCCFixSmallEdges", "OCCFixSmallFaces"):
    gmsh.option.setNumber("Geometry." + o, 1)
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-3)
inst = json.load(open(os.path.join(CAD, "instances.json")))["instances"]


def load(part):
    return [t for d, t in occ.importShapes(os.path.join(CAD, part + ".step")) if d == 3]


def place(part, base=None):
    tags, base = [], base or load(part)
    for i in inst:
        if i["part"] != part:
            continue
        cp = occ.copy([(3, t) for t in base])
        occ.affineTransform(cp, list(np.hstack([np.array(i["R"]), np.array(i["t"])[:, None]]).ravel()))
        tags += [c[1] for c in cp]
    occ.remove([(3, t) for t in base], recursive=True)
    return tags


if "--from-brep" in sys.argv:              # re-mesh the saved boolean result (motor_detailed.brep + .json)
    for o in ("OCCFixDegenerated", "OCCFixSmallEdges", "OCCFixSmallFaces"):
        gmsh.option.setNumber("Geometry." + o, 0)   # reload exactly what was written
    gmsh.merge(os.path.join(OUT, "motor_detailed.brep")); occ.synchronize()
    regions = json.load(open(os.path.join(OUT, "motor_detailed.brep.json")))
    rank = {t: k + 1 for k, t in enumerate(sorted(t for ts in regions.values() for t in ts))}   # reload renumbers 1..N
    regions = {n: [rank[t] for t in ts] for n, ts in regions.items()}
    owner = {t: n for n, ts in regions.items() for t in ts}
    assert set(owner) == {t for _, t in gmsh.model.getEntities(3)}, "volume tags changed on reload"
else:
    groups = {}
    oring = occ.cut([(3, occ.addCylinder(0, 0, 70.5, 0, 0, 5, 82.5))], [(3, occ.addCylinder(0, 0, 69, 0, 0, 8, 80.0))])[0]
    hs, _ = occ.fuse([(3, t) for t in load("housing")], [(3, t) for t in load("rear_cover")] + oring)
    groups["housing"] = [t for _, t in hs]
    groups["shaft"] = load("shaft")
    groups["bearings"] = []
    for i in inst:                                  # ponytail: bearings as 52/30 x 15 steel rings (STEP shields don't mesh)
        if i["part"] == "bearing_52x30x15":
            z0 = i["t"][2]
            o, h = occ.addCylinder(0, 0, z0, 0, 0, 15, 26.0), occ.addCylinder(0, 0, z0 - 1, 0, 0, 17, 15.0)
            groups["bearings"] += [t for _, t in occ.cut([(3, o)], [(3, h)])[0]]
    groups["magnets"] = place("magnet_ferrite")
    # ponytail: the CAD bobbins float 0.10-0.25 mm off the tooth and carry sub-mm lips and overlapping micro-faces (bobbin_B
    # alone does not mesh); every slot fragment with them failed (PLC / overlapping facets). Simplified bobbin in the tooth
    # frame instead: neck sleeve with shoe/yoke flanges (|x| 8.7 = CAD wall 1.45 mm) and stepped end walls under the end
    # turns, minus the tooth, so it shares the tooth faces exactly; >= 0.27 mm from the wire everywhere. 4457 vs 4773 mm3.
    def simple_bobbin(tooth):
        b = [occ.addBox(-8.7, 54.0, -32.5, 17.4, 17.5, 65.0)]
        for z0, z1, xh in ((32.5, 34.5, 8.0), (34.5, 35.5, 7.25)):
            b += [occ.addBox(-xh, 54.0, z0, 2 * xh, 17.5, z1 - z0), occ.addBox(-xh, 54.0, -z1, 2 * xh, 17.5, z1 - z0)]
        u, _ = occ.fuse([(3, b[0])], [(3, t) for t in b[1:]])
        return [t for _, t in occ.cut(u, [(3, t) for t in tooth], removeTool=False)[0]]


    tooth = load("tooth_65")
    bobbin = simple_bobbin(tooth)
    teeth = place("tooth_65", tooth)
    st, _ = occ.fuse([(3, teeth[0])], [(3, t) for t in teeth[1:]])
    groups["stator"] = [t for _, t in st]
    # ponytail: the STEP coil is ONE swept B-spline face 2 m long whose turns sit 0.1 mm apart; every OCC boolean against
    # it stalls (Oct 15 run). Re-sweep the same centreline (coil_65_centreline.npy, the CAD sweep path) as a pipe split
    # into ~SEG mm faces: same geometry, booleans become local. R_WIRE 1.45 = bare 2.9 mm copper; the 0.05 mm enamel
    # shell becomes part of the resin around it (k 0.22 vs 0.25), so make_case puts no extra enamel layer on the coil.
    R_WIRE, SEG = float(os.environ.get("R_WIRE", 1.45)), 5.0   # SEG 40: 215 s per coil-bobbin pair, 10: 43 s, 5: 26 s


    def sweep_coil():
        c = np.load(os.path.join(CAD, "coil_65_centreline.npy"))
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
        u = np.linspace(0, s[-1], int(round(s[-1])) + 1)                      # 1 mm resampling
        p = np.c_[[np.interp(u, s, c[:, k]) for k in range(3)]].T
        p = np.r_[[p[0] + [0, 0, 0.05]], p]           # S lead end 48.75 -> flush with the strap top 48.8 (no 0.05 mm cap)
        pts = [occ.addPoint(*q) for q in p]
        cut = np.linspace(0, len(p) - 1, int(round(s[-1] / SEG)) + 1).astype(int)
        out, _ = occ.fragment([(1, occ.addSpline(pts))], [(0, pts[k]) for k in cut[1:-1]])   # split one C2 spline
        edges = sorted(t for d, t in out if d == 1)
        occ.synchronize(); occ.remove([(0, q) for q in pts if (0, q) in gmsh.model.getEntities(0)])
        t0 = (p[1] - p[0]) / np.linalg.norm(p[1] - p[0])
        d = occ.addDisk(*p[0], R_WIRE, R_WIRE, zAxis=list(t0))
        v = [t for dd, t in occ.addPipe([(2, d)], occ.addWire(edges, checkClosed=False), "DiscreteTrihedron") if dd == 3]
        tags = []
        for i in inst:
            if i["part"] == "04_coil_65":
                cp = occ.copy([(3, t) for t in v])
                occ.affineTransform(cp, list(np.hstack([np.array(i["R"]), np.array(i["t"])[:, None]]).ravel()))
                tags += [c[1] for c in cp]
        occ.remove([(3, t) for t in v], recursive=True)
        return tags


    groups["coil"] = sweep_coil()
    groups["bobbin"] = place("tooth_65", bobbin)
    groups["busbar"] = place("busbar_L1_65") + place("busbar_L2_65") + place("busbar_L3_65")
    groups["strap"] = place("link_strap_65")
    groups["tbar"] = place("terminal_bar_L1") + place("terminal_bar_L2") + place("terminal_bar_L3")
    # welds: each lead sits in a 3.2 mm hole with 0.1 mm clearance in the CAD; built, it is welded. A Cu plug of r 1.62
    # fills the hole over the plate/strap thickness (lead positions from the coil STEP, coil frame: S lead ends in its
    # strap z 46.7-48.8, F lead runs through its net plate z 49.7-53.5)
    LEADS = {"strap": ((7.156, 73.653), 46.7, 48.8), "busbar": ((15.774, 65.555), 49.7, 53.5)}
    for i in inst:
        if i["part"] != "04_coil_65":
            continue
        R = np.array(i["R"])
        for grp, ((lx, ly), z0, z1) in LEADS.items():
            x, y, _ = R @ np.array([lx, ly, 0.0])
            groups[grp].append(occ.addCylinder(x, y, z0, 0, 0, z1 - z0, 1.62))
    for grp in ("strap", "busbar"):               # fuse the plugs into their plates: no 0.02 mm hole/plug skins
        g = [(3, t) for t in groups[grp]]
        groups[grp] = [t for _, t in occ.fuse(g[:1], g[1:])[0]]

    rc = occ.addCylinder(0, 0, -ROTOR_Z, 0, 0, 2 * ROTOR_Z, R_BORE)
    bore = occ.addCylinder(0, 0, -ROTOR_Z - 1, 0, 0, 2 * ROTOR_Z + 2, 15.0)
    r, _ = occ.cut([(3, rc)], [(3, bore)] + [(3, t) for t in groups["magnets"]], removeTool=False)
    occ.remove([(3, bore)])
    groups["rotor"] = [t for _, t in r]

    # impregnation resin: envelope per slot minus everything solid in it
    angs = [math.degrees(math.atan2(i["R"][1][1], i["R"][0][1])) for i in inst if i["part"] == "tooth_65"]
    env = []
    for ang in angs:
        blk = occ.addBox(-E_X, E_Y[0], -E_Z, 2 * E_X, E_Y[1] - E_Y[0], 2 * E_Z)
        a = math.radians(15)
        wedge = occ.addCylinder(0, 0, -60, 0, 0, 120, 100, angle=2 * a)
        occ.rotate([(3, wedge)], 0, 0, 0, 0, 0, 1, math.pi / 2 - a)
        w, _ = occ.intersect([(3, blk)], [(3, wedge)])
        occ.rotate(w, 0, 0, 0, 0, 0, 1, math.radians(ang - 90))
        env += w
    def overlaps(a, b):
        a, b = occ.getBoundingBox(*a), occ.getBoundingBox(*b)
        return all(a[k] <= b[k + 3] and b[k] <= a[k + 3] for k in range(3))


    tools = [(3, t) for g in ("stator", "coil", "bobbin", "strap", "busbar") for t in groups[g]]
    groups["resin"] = []
    for w in env:                                  # slot by slot, local tools only: keeps the boolean memory down
        rs, _ = occ.cut([w], [x for x in tools if overlaps(w, x)], removeTool=False)
        groups["resin"] += [t for _, t in rs]
    occ.synchronize()
    print("resin cut", f"{time.time() - T0:.0f} s", flush=True)

    cav = occ.addCylinder(0, 0, CAV_Z[0], 0, 0, CAV_Z[1] - CAV_Z[0], CAV_R)
    c, _ = occ.cut([(3, cav)], [(3, t) for g in groups.values() for t in g], removeTool=False)
    groups["inair"] = [t for _, t in c]
    occ.synchronize()

    flat = [t for g in groups.values() for t in g]
    assert len(flat) == len(set(flat)), "tag shared between groups"
    print({n: len(g) for n, g in groups.items()}, f"{time.time() - T0:.0f} s", flush=True)

    allparts = [(3, t) for t in flat]
    out, omap = occ.fragment(allparts, [])
    print(f"fragment done {time.time() - T0:.0f} s", flush=True)
    occ.synchronize()
    owner = {}
    for (d, t), children in zip(allparts, omap):
        name = next(n for n, g in groups.items() if t in g)
        for ch in children:
            owner.setdefault(ch[1], name)          # first claim wins: overlaps (if any) stay with the earlier group
    regions = {n: [] for n in groups}
    for t, n in owner.items():
        regions[n].append(t)
    live = {t for _, t in gmsh.model.getEntities(3)}
    orphans = live - set(owner)
    print("orphan volumes (outside every group):", len(orphans))
    occ.remove([(3, t) for t in orphans], recursive=True)
    occ.synchronize()

BREP = os.path.join(OUT, "motor_detailed.brep")
if "--from-brep" not in sys.argv:              # the booleans take ~1 h: keep their result for re-meshing
    gmsh.write(BREP)
    json.dump({n: sorted(ts) for n, ts in regions.items()}, open(BREP + ".json", "w"))
# volumes bounded by the identical set of surfaces make HXT fail ("duplicate volume ... in reconstructed Brep")
seen = {}
for _, t in gmsh.model.getEntities(3):
    key = frozenset(abs(f) for _, f in gmsh.model.getBoundary([(3, t)], oriented=False))
    if key in seen:
        print("DUPLICATE volumes", seen[key], t, [owner.get(x) for x in (seen[key], t)],
              "%.4f %.4f mm3" % (occ.getMass(3, seen[key]), occ.getMass(3, t)), np.round(occ.getBoundingBox(3, t), 2))
    seen[key] = t

info = {}
for n, ts in regions.items():
    gmsh.model.addPhysicalGroup(3, ts, name=n)
    info[n] = sum(occ.getMass(3, t) for t in ts) * 1e-9
    print(f"{n:9s} pieces {len(ts):4d}  volume {info[n]*1e6:9.2f} cm3")
if "--geo-only" in sys.argv:
    sys.exit(0)

gmsh.option.setNumber("Mesh.MeshSizeMin", 0.25)
gmsh.option.setNumber("Mesh.MeshSizeMax", H)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 8)    # ~1.1 mm around the 2.9 mm wire
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
fields = []
for names, size in ((("coil", "resin", "bobbin"), HW), (("busbar", "strap", "tbar"), HB)):
    f = gmsh.model.mesh.field.add("Constant")
    gmsh.model.mesh.field.setNumbers(f, "VolumesList", [t for n in names for t in regions[n]])
    gmsh.model.mesh.field.setNumber(f, "VIn", size)
    gmsh.model.mesh.field.setNumber(f, "VOut", 1e9)
    fields.append(f)
fmin = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(fmin, "FieldsList", fields)
gmsh.model.mesh.field.setAsBackgroundMesh(fmin)
gmsh.option.setNumber("Mesh.Algorithm", 6)
gmsh.option.setNumber("Mesh.Algorithm3D", int(os.environ.get("ALG3D", 1)))   # HXT (10) failed on the full model
gmsh.option.setNumber("General.NumThreads", int(os.environ.get("NTHREADS", 1)))
gmsh.option.setNumber("Mesh.Optimize", 1)
gmsh.model.mesh.generate(3)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.SaveAll", 0)
os.makedirs(OUT, exist_ok=True)
gmsh.write(os.path.join(OUT, "motor_detailed.msh"))
_, et, _ = gmsh.model.mesh.getElements(3)
info["_cells"] = int(sum(len(e) for e in et))
json.dump(info, open(os.path.join(OUT, "motor_detailed_regions.json"), "w"), indent=1)
print("tets:", info["_cells"])

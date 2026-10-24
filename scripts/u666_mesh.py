"""Mesh the U666 region set (u666_geo.py output) with gmsh: solids (thermal model) or outside air (natural-convection CFD).

    .venv/Scripts/python -I scripts/u666_mesh.py --solids [--size 2.5]   -> mesh/u666/u666_solids.msh + _regions.json
    .venv/Scripts/python -I scripts/u666_mesh.py --solids --stl          -> mesh/u666/stl/<region>.stl + skin.stl (2D only, for snappy)
    .venv/Scripts/python -I scripts/u666_mesh.py --air                   -> mesh/u666/u666_air.msh (patches motor/ambient)
Delaunay 3D, 1 thread (KNOWN_ISSUES #6, RAM). Physical volumes = regions; slot/endw/rpocket are separate physical
groups (cellZones) that u666_prep_base.sh merges into the winding / rotor regions.
"""
import gmsh, json, os, sys
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh", "u666")
AIR = "--air" in sys.argv
H = float(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 2.5
SIZE = {"housing": H * 1.2, "inair": H * 1.2, "stator": H * 0.8, "slot": H * 0.6, "endw": H * 0.6,
        "wedge": H * 0.2, "seal": H * 0.6, "rotor": H * 0.6, "rpocket": H * 0.4, "magnets": H * 0.6, "endcaps": H * 0.8,
        "shaft": H, "bearing_f": H * 0.8, "bearing_r": H * 0.8}

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 1)
gmsh.option.setNumber("General.Verbosity", int(os.environ.get("VERB", 5)))
for o in ("OCCFixDegenerated", "OCCFixSmallEdges", "OCCFixSmallFaces"):
    gmsh.option.setNumber("Geometry." + o, 0)
occ, M = gmsh.model.occ, gmsh.model
gmsh.merge(os.path.join(OUT, "u666_geo.brep"))
occ.synchronize()
regions = json.load(open(os.path.join(OUT, "u666_geo.brep.json")))
rank = {t: k + 1 for k, t in enumerate(sorted(t for ts in regions.values() for t in ts))}   # reload renumbers 1..N
regions = {n: [rank[t] for t in ts] for n, ts in regions.items()}
assert {t for ts in regions.values() for t in ts} == {t for _, t in M.getEntities(3)}, "volume tags changed"
bbs = np.array([M.getBoundingBox(3, t) for t in regions["air"]])   # air = box piece + small outside pockets
BOX = [*bbs[:, :3].min(0), *bbs[:, 3:].max(0)]
bz = lambda t: sum(M.getBoundingBox(3, t)[2::3]) / 2
regions["bearing_f"] = [t for t in regions["bearings"] if bz(t) > 30]      # 6205 front (z 78..93)
regions["bearing_r"] = [t for t in regions.pop("bearings") if bz(t) <= 30]  # 6003 rear (z -30..-20)

if AIR:
    occ.remove([(3, t) for n, ts in regions.items() if n != "air" for t in ts])   # keep the shared faces
    occ.synchronize()
    regions = {"air": regions["air"]}
    amb, mot = [], []
    for _, f in M.getBoundary([(3, t) for t in regions["air"]], oriented=False):
        b = M.getBoundingBox(2, abs(f))
        on = any(abs(b[i] - BOX[i]) < 1e-3 and abs(b[i + 3] - BOX[i]) < 1e-3 or
                 abs(b[i] - BOX[i + 3]) < 1e-3 and abs(b[i + 3] - BOX[i + 3]) < 1e-3 for i in range(3))
        (amb if on else mot).append(abs(f))
    M.addPhysicalGroup(2, amb, name="ambient")
    M.addPhysicalGroup(2, mot, name="motor")
    print("ambient faces", len(amb), "motor faces", len(mot))
else:
    occ.remove([(3, t) for t in regions.pop("air")])
    occ.synchronize()
    # defeature degenerate skin faces (|area| < 0.01 mm2, non-planar, one volume once the air is gone), e.g. the
    # inverted torus at the terminal-box rim (z -85) that gmsh cannot mesh ("1D mesh not a closed loop")
    nshared = lambda: sum(1 for _, s in M.getEntities(2) if len(M.getAdjacencies(2, s)[0]) == 2)
    degen = [(f, M.getAdjacencies(2, f)[0][0]) for _, f in M.getEntities(2) if len(M.getAdjacencies(2, f)[0]) == 1
             and abs(occ.getMass(2, f)) < 1e-2 and M.getType(2, f) != "Plane"]
    print("degenerate skin faces:", degen, flush=True)
    for f, v in degen:
        if True:
            s0 = nshared()
            new = [t for d, t in occ.defeature([v], [f]) if d == 3]
            occ.synchronize()
            for ts in regions.values():
                if v in ts:
                    ts[ts.index(v):ts.index(v) + 1] = new
            print("defeatured skin face", f, "of volume", v, "->", new, "shared faces", s0, "->", nshared(), flush=True)
    # same-region slivers: the shaft is split by a r 14.96 face 0.07 mm inside the rotor bore (r 15.03, z -2.2..60.35)
    # -> 0.07 mm shells whose end circles cross in the 1D mesh (face 5185, z -2.2) -> "PLC Error" in 3D. Fuse the
    # pieces of these regions. 2026-10-23 MESH2: FUSE=shaft broke conformity (skin faces 311 -> 442) -> off by default
    nskin = lambda: sum(1 for _, s in M.getEntities(2) if len(M.getAdjacencies(2, s)[0]) == 1)
    for n in [s for s in os.environ.get("FUSE", "").split(",") if s]:
        ts = regions[n]
        if len(ts) < 2:
            continue
        k0, s0 = nskin(), nshared()
        new = [t for d, t in occ.fuse([(3, ts[0])], [(3, t) for t in ts[1:]])[0] if d == 3]
        occ.synchronize()
        regions[n] = new
        print("fused", n, len(ts), "->", len(new), "pieces; skin faces", k0, "->", nskin(), "shared", s0, "->", nshared(), flush=True)

# --group G: NON-CONFORMAL route (MESH2). Mesh one final region alone (its zones stay conformal inside it); boundary
# faces become physical surfaces "<G>_to_<neighbour group>" (mapped/AMI couples in OpenFOAM) or "outside" (skin).
# The conformal one-shot 3D fails (PLC) on the shaft shell 0.07 mm thick (press fit r 15.03 vs bore 14.96); alone,
# the shaft pieces can be fused without breaking any interface.
GROUPS = {"winding": ["slot", "endw"], "wedge": ["wedge", "seal"], "rotor": ["rotor", "rpocket"],
          "bearings": ["bearing_f", "bearing_r"]}
GRP = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else None
flab = {}
if GRP:
    gof = {t: next((k for k, v in GROUPS.items() if n in v), n) for n, ts in regions.items() for t in ts}
    mine = GROUPS.get(GRP, [GRP])
    myv = {t for n in mine for t in regions[n]}
    def samples(f):   # points on the trimmed face (5x5 parameter grid, isInside), for labelling faces after a fuse
        lo, hi = M.getParametrizationBounds(2, f)
        uv = [(lo[0] + (hi[0] - lo[0]) * a, lo[1] + (hi[1] - lo[1]) * b) for a in (.1, .3, .5, .7, .9) for b in (.1, .3, .5, .7, .9)]
        xyz = np.array(M.getValue(2, f, [x for q in uv for x in q])).reshape(-1, 3)
        return [x for x in xyz if M.isInside(2, f, list(x))]
    lab, spts, lsig = {}, [], {}
    for _, f in M.getBoundary([(3, t) for t in myv], combined=True, oriented=False):
        up = [u for u in M.getAdjacencies(2, abs(f))[0] if u not in myv]
        lab[abs(f)] = GRP + "_to_" + gof[up[0]] if up else "outside"
        lsig[abs(f)] = (round(occ.getMass(2, abs(f)), 4), tuple(np.round(occ.getCenterOfMass(2, abs(f)), 3)))
        spts += [(x, lab[abs(f)]) for x in samples(abs(f))]
    occ.remove([(3, t) for _, t in M.getEntities(3) if t not in myv], recursive=True)
    occ.synchronize()
    regions = {n: regions[n] for n in mine}
    # BASE2 z-PRISM route (EXTRUDE groups): every zone volume is a z-prism (one lamination profile extruded; endw is an
    # annular prism). Mid-z section of each volume -> 2D fragment (conformal, overlaps of slot/endw sections split) ->
    # triangles x z-layers (DZ) = prisms aligned with the axial anisotropy (no tet cross-diffusion). Band limits closer
    # than SNAPZ (0.01-0.19 mm CAD steps at the magnet/rotor ends) are merged. Boundary faces get the label of the
    # nearest original face (lab). Writes the same u666_g_<G>.msh (msh 2.2, prisms) as the tet route.
    if GRP in os.environ.get("EXTRUDE", "winding,stator,rotor,magnets,wedge").split(","):
        DZ, SNAP, ZREF = float(os.environ.get("DZ", 2.5)), float(os.environ.get("SNAPZ", 0.5)), -1000.0
        vols = [(n, t, M.getBoundingBox(3, t)) for n in mine for t in regions[n]]
        zs = sorted(z for _, _, b in vols for z in (b[2], b[5]))
        cl = [[zs[0]]]
        for z in zs[1:]:
            (cl[-1].append(z) if z - cl[-1][-1] < SNAP else cl.append([z]))
        snap = lambda z: next(round(float(np.mean(c)), 4) for c in cl if c[0] - 1e-9 <= z <= c[-1] + 1e-9)
        secs, owner = [], []
        for n, t, b in vols:
            zm = (b[2] + b[5]) / 2
            r = occ.addRectangle(b[0] - 1, b[1] - 1, zm, b[3] - b[0] + 2, b[4] - b[1] + 2)
            s = [x for x in occ.intersect([(2, r)], [(3, t)], removeTool=False)[0] if x[0] == 2]
            occ.translate(s, 0, 0, ZREF - zm)
            z0, z1 = snap(b[2]), snap(b[5])
            occ.synchronize()
            A = sum(occ.getMass(2, f) for _, f in s)
            err = A * (b[5] - b[2]) / occ.getMass(3, t) - 1
            if abs(err) > 0.01:
                print("WARN non-prism volume", n, t, "A*L/V-1 = %.4f" % err, flush=True)
            secs += s
            owner += [(n, z0, z1)] * len(s)
        # BASE3 S8c tooth-tip fix (TIP="r_tip,half-angle deg,pitch deg,r_rotor"; TIP=0 = off). The wedge ring was
        # annulus 43.53..44 minus stator: a 5 um strip under every tooth tip (r_tip 43.535) -> 2-5 um sliver prisms,
        # -88 W non-conservative stator|wedge pair. Wedge section = CAD wedge + slot-opening sectors whose inner arc IS
        # the tip radius (strip cut off). Rotor (r 43.53) then couples to the tips directly: its arc is split at the
        # tip angles (probe: 72 tip ends at 10k +- 3.226838 deg) and relabelled rotor_to_stator / stator_to_rotor.
        TIP = None if os.environ.get("TIP") == "0" else [float(x) for x in os.environ.get("TIP", "43.535,3.226838,10,43.53").split(",")]
        tpts = []
        if TIP and GRP == "wedge":
            dk = occ.addDisk(0, 0, ZREF, TIP[0], TIP[0])
            ns, no = [], []
            for s, w in zip(secs, owner):
                r = [x for x in occ.cut([s], [(2, dk)], removeTool=False)[0] if x[0] == 2] if w[0] == "wedge" else [s]
                ns += r
                no += [w] * len(r)
            occ.remove([(2, dk)])
            secs, owner = ns, no
        if TIP and GRP == "rotor":
            tpts = [(0, occ.addPoint(TIP[3] * np.cos(a), TIP[3] * np.sin(a), ZREF)) for k in range(int(round(360 / TIP[2])))
                    for a in (np.radians(k * TIP[2] - TIP[1]), np.radians(k * TIP[2] + TIP[1]))]
        # union per (zone, z-band) first: same-zone CAD pieces overlap by 2-20 um (wedge pieces r 43.5315 vs gap ring
        # r 43.535) -> sliver triangles 2 um high (huge kappa/delta next to the stator: -88 W non-conservative
        # stator|wedge pair). The union removes the overlap strips; then fragment across zones/bands.
        gmsh.option.setNumber("Geometry.ToleranceBoolean", float(os.environ.get("BOOLTOL", 0.03)))
        us, uo = [], []
        for o in sorted(set(owner)):
            ss = [s for s, w in zip(secs, owner) if w == o]
            if len(ss) > 1:
                ss = [x for x in occ.fuse(ss[:1], ss[1:])[0] if x[0] == 2]
            us += ss
            uo += [o] * len(ss)
        secs, owner = us, uo
        out, omap = occ.fragment(secs, tpts) if len(secs) + len(tpts) > 1 else (secs, [secs])   # 1 face (fused stator): fragment returns no map
        gmsh.option.setNumber("Geometry.ToleranceBoolean", 0)
        occ.synchronize()
        fz = {}
        for k, ch in enumerate(omap[:len(secs)]):
            for d, f in ch:
                fz.setdefault(f, set()).add(owner[k])
        print("prism route", GRP, "volumes", len(vols), "section faces", len(fz), "bands", [snap(c[0]) for c in cl], flush=True)
        for f, zz in fz.items():   # thin section faces (mean width 2A/perimeter < 0.05 mm) -> sliver prisms
            per = sum(occ.getMass(1, abs(c)) for _, c in M.getBoundary([(2, f)], oriented=False))
            if 2 * occ.getMass(2, f) / per < 0.05:
                print("  thin section face", f, "area %.4f perim %.2f" % (occ.getMass(2, f), per), sorted(zz), flush=True)
        M.setVisibility(M.getEntities(), 0)
        M.setVisibility([(2, f) for f in fz], 1, recursive=True)
        gmsh.option.setNumber("Mesh.MeshOnlyVisible", 1)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeMax", H)
        fl = []
        for n in mine:
            fc = M.mesh.field.add("Constant")
            M.mesh.field.setNumbers(fc, "SurfacesList", [f for f, zz in fz.items() if any(o[0] == n for o in zz)])
            M.mesh.field.setNumber(fc, "VIn", SIZE.get(n, H))
            M.mesh.field.setNumber(fc, "VOut", 1e9)
            M.mesh.field.setNumber(fc, "IncludeBoundary", 1)
            fl.append(fc)
        fmin = M.mesh.field.add("Min")
        M.mesh.field.setNumbers(fmin, "FieldsList", fl)
        M.mesh.field.setAsBackgroundMesh(fmin)
        gmsh.option.setNumber("Mesh.Algorithm", int(os.environ.get("ALG2D", 6)))
        M.mesh.generate(2)
        nt, nc, _ = M.mesh.getNodes()
        X2 = {int(a): np.array(nc[3 * i:3 * i + 2]) for i, a in enumerate(nt)}
        Z = [snap(cl[0][0])]
        for c in cl[1:]:
            z = snap(c[0])
            nl = max(1, int(round((z - Z[-1]) / DZ)))
            Z += list(np.linspace(Z[-1], z, nl + 1)[1:])
        nid, P = {}, []
        def node(a, k):
            if (a, k) not in nid:
                nid[(a, k)] = len(P) + 1
                P.append((*X2[a], Z[k]))
            return nid[(a, k)]
        cells, faces = [], {}
        for f, zz in fz.items():
            _, _, en = M.mesh.getElements(2, f)
            tri = np.array(en[0], dtype=int).reshape(-1, 3)
            for k in range(len(Z) - 1):
                zc = 0.5 * (Z[k] + Z[k + 1])
                zone = [o[0] for o in zz if o[1] < zc < o[2]]
                if not zone:
                    continue
                if len(set(zone)) > 1:
                    print("WARN overlapping zones", zone, "face", f, flush=True)
                for a, b, c in tri:
                    u, w = X2[b] - X2[a], X2[c] - X2[a]
                    if u[0] * w[1] - u[1] * w[0] < 0:
                        b, c = c, b
                    v = [node(a, k), node(b, k), node(c, k), node(a, k + 1), node(b, k + 1), node(c, k + 1)]
                    cells.append((zone[0], v))
                    for fv in (v[:3], v[3:], [v[0], v[1], v[4], v[3]], [v[1], v[2], v[5], v[4]], [v[2], v[0], v[3], v[5]]):
                        key = tuple(sorted(fv))
                        faces[key] = None if key in faces else fv
        bnd = [fv for fv in faces.values() if fv is not None]
        Pa = np.array(P)
        cen = np.array([Pa[np.array(fv) - 1].mean(0) for fv in bnd])
        cen3 = cen
        # labels from the TET mesh of the same group (tet_bak/u666_g_<G>.msh, exact CAD-surface patches): nearest patch
        # triangle (12 nearest centroids, exact point-triangle distance). gmsh getClosestPoint/isInside on the CAD faces
        # mislabel (untrimmed planes; isInside true outside holed cylinders, wedge/rotor gap ring)
        from scipy.spatial import cKDTree
        cur = M.getCurrent()
        gmsh.model.add("tetref")
        gmsh.merge(os.environ.get("TETREF", os.path.join(OUT, "tet_bak", "u666_g_%s.msh" % GRP)))
        tn, tc, _ = gmsh.model.mesh.getNodes()
        TX = np.zeros((int(tn.max()) + 1, 3))
        TX[tn.astype(int)] = np.array(tc).reshape(-1, 3)
        TP, TL = [], []
        for d2, pg in gmsh.model.getPhysicalGroups(2):
            nm = gmsh.model.getPhysicalName(d2, pg)
            for e in gmsh.model.getEntitiesForPhysicalGroup(2, pg):
                _, _, en = gmsh.model.mesh.getElements(2, e)
                t3 = TX[np.array(en[0]).astype(int).reshape(-1, 3)]
                TP.append(t3)
                TL += [nm] * len(t3)
        gmsh.model.remove()
        gmsh.model.setCurrent(cur)
        TP, TL = np.concatenate(TP), np.array(TL)
        _, ii = cKDTree(TP.mean(1)).query(cen3, k=12)
        a, b, c = TP[ii, 0], TP[ii, 1], TP[ii, 2]
        q = cen3[:, None, :]
        nn = np.cross(b - a, c - a)
        nn = nn / np.maximum(np.linalg.norm(nn, axis=2, keepdims=True), 1e-30)
        h = ((q - a) * nn).sum(2)
        pr = q - h[..., None] * nn
        ins = np.ones(h.shape, bool)
        for u, v in ((a, b), (b, c), (c, a)):
            ins &= (np.cross(v - u, pr - u) * nn).sum(2) >= -1e-9
        edge = np.minimum(np.linalg.norm(q - a, axis=2), np.minimum(np.linalg.norm(q - b, axis=2), np.linalg.norm(q - c, axis=2)))
        dd = np.where(ins, np.abs(h), edge)
        blab = list(TL[ii[np.arange(len(ii)), dd.argmin(1)]])
        if TIP and GRP in ("stator", "rotor"):   # tooth-tip pair (see TIP above); chord centroids sit < 6 um inside the arcs
            rc, th = np.hypot(cen3[:, 0], cen3[:, 1]), np.degrees(np.arctan2(cen3[:, 1], cen3[:, 0]))
            ontip = np.abs((th + TIP[2] / 2) % TIP[2] - TIP[2] / 2) < TIP[1]
            for i, l in enumerate(blab):
                if GRP == "stator" and l == "stator_to_wedge" and rc[i] < TIP[0] + 0.002:
                    blab[i] = "stator_to_rotor"
                if GRP == "rotor" and l == "rotor_to_wedge" and rc[i] > TIP[3] - 0.02 and ontip[i]:
                    blab[i] = "rotor_to_stator"
        names = sorted(set(blab))
        def farea(fv):
            p = Pa[np.array(fv) - 1]
            return 0.5 * np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) + (0.5 * np.linalg.norm(np.cross(p[2] - p[0], p[3] - p[0])) if len(fv) == 4 else 0)
        pa, ca = {}, {}
        for fv, l in zip(bnd, blab):
            pa[l] = pa.get(l, 0) + farea(fv)
        for g, l in lab.items():
            ca[l] = ca.get(l, 0) + occ.getMass(2, g)
        print("patch area mm2 (prism | CAD):", {l: (round(pa.get(l, 0)), round(ca.get(l, 0))) for l in set(ca) | set(pa)}, flush=True)
        zid = {n: k + 1 for k, n in enumerate(mine)}
        pid = {p: len(mine) + 1 + k for k, p in enumerate(names)}
        name = "u666_g_" + GRP
        with open(os.path.join(OUT, name + ".msh"), "w") as fo:
            fo.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n%d\n" % (len(zid) + len(pid)))
            fo.write("".join('2 %d "%s"\n' % (i, p) for p, i in pid.items()) + "".join('3 %d "%s"\n' % (i, n) for n, i in zid.items()))
            fo.write("$EndPhysicalNames\n$Nodes\n%d\n" % len(P) + "".join("%d %.9g %.9g %.9g\n" % (i + 1, *p) for i, p in enumerate(P)))
            fo.write("$EndNodes\n$Elements\n%d\n" % (len(bnd) + len(cells)))
            e = 0
            for fv, l in zip(bnd, blab):
                e += 1
                fo.write("%d %d 2 %d %d %s\n" % (e, 2 if len(fv) == 3 else 3, pid[l], pid[l], " ".join(map(str, fv))))
            for zn, v in cells:
                e += 1
                fo.write("%d 6 2 %d %d %s\n" % (e, zid[zn], zid[zn], " ".join(map(str, v))))
            fo.write("$EndElements\n")
        from collections import Counter
        vz = Counter()
        for zn, v in cells:
            p = Pa[np.array(v) - 1]
            u, w = p[1] - p[0], p[2] - p[0]
            vz[zn] += 0.5 * abs(u[0] * w[1] - u[1] * w[0]) * (p[3, 2] - p[0, 2]) * 1e-9
        info = {n: vz[n] for n in mine}
        info["_cells"] = len(cells)
        json.dump(info, open(os.path.join(OUT, name + "_regions.json"), "w"), indent=1)
        print("prisms:", len(cells), "volumes cm3", {n: round(v * 1e6, 2) for n, v in vz.items()},
              "patches", dict(Counter(blab)), flush=True)
        gmsh.finalize()
        sys.exit(0)
    # fuse only the thin pieces (2V/A < 0.05 mm: the 0.07 mm shaft shells) with their same-region neighbours
    for n, ts in regions.items():
        if n not in os.environ.get("GFUSE", "shaft,endcaps,wedge,housing").split(","):
            continue
        thin = [t for t in ts if 2 * occ.getMass(3, t) / sum(occ.getMass(2, abs(f)) for _, f in M.getBoundary([(3, t)], oriented=False)) < float(os.environ.get("THIN", 0.2))]
        nb = {u for t in thin for _, f in M.getBoundary([(3, t)], oriented=False) for u in M.getAdjacencies(2, abs(f))[0] if u in ts}
        if len(nb) > 1:
            out = [t for d, t in occ.fuse([(3, min(nb))], [(3, t) for t in nb if t != min(nb)])[0] if d == 3]
            occ.synchronize()
            regions[n] = [t for t in ts if t not in nb] + out
            print("group fuse", n, sorted(nb), "->", out, flush=True)
    allv = [(3, t) for ts in regions.values() for t in ts]
    bf = [abs(f) for _, f in M.getBoundary(allv, combined=True, oriented=False)]
    pat, mixed = {}, []
    sx = np.array([s[0] for s in spts])
    for f in bf:
        if f in lab and lsig[f] == (round(occ.getMass(2, f), 4), tuple(np.round(occ.getCenterOfMass(2, f), 3))):   # untouched (tags can be reused after a fuse)
            pat.setdefault(lab[f], []).append(f)
            continue
        b = np.array(M.getBoundingBox(2, f))
        cand = np.nonzero(np.all((sx > b[:3] - 1e-3) & (sx < b[3:] + 1e-3), axis=1))[0]
        ls = {spts[i][1] for i in cand if np.linalg.norm(np.array(M.getClosestPoint(2, f, list(sx[i]))[0]) - sx[i]) < 1e-4}
        if len(ls) > 1:   # fused face spanning two neighbours: split per triangle after meshing
            mixed.append((f, sorted(ls)))
        else:
            pat.setdefault(sorted(ls)[0] if ls else "outside", []).append(f)
    print("group", GRP, "volumes", len(allv), "boundary faces", len(bf), "mixed faces", mixed, flush=True)

info = {}
for n, ts in regions.items():
    M.addPhysicalGroup(3, ts, name=n)
    info[n] = sum(occ.getMass(3, t) for t in ts) * 1e-9
    print(f"{n:9s} pieces {len(ts):4d}  volume {info[n]*1e6:9.2f} cm3", flush=True)

gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)
# proximity sizing: CAD vertices closer than the cell size (concentric circles 0.07 mm apart at the shaft, fin and
# lug details on the housing) gave crossing 1D edges -> invalid surface mesh -> "PLC Error" in 3D. Each vertex gets a
# size of PROX x its nearest-vertex distance (0.1 .. H).
from scipy.spatial import cKDTree
vt = [t for _, t in M.getEntities(0)]
xyz = np.array([M.getValue(0, t, []) for t in vt])
dnn = cKDTree(xyz).query(xyz, k=2)[0][:, 1]
# B-spline lug face on the housing (x -90, y 24, z -5) whose curves cross in parameter space when refined: it hangs
# gmsh at fine sizes (meshes at ~H with no curvature sizing): its vertices are kept out of the proximity sizing
SKIP = [int(s) for s in os.environ.get("PROX_SKIP_SURF", "1428").split(",") if s] if not AIR else []
SKIP = [s for s in SKIP if (2, s) in M.getEntities(2)]
for s in SKIP:   # no proximity balls within 2 H of that face
    b = np.array(M.getBoundingBox(2, s))
    near = np.all((xyz > b[:3] - 2 * H) & (xyz < b[3:] + 2 * H), axis=1)
    dnn = np.where(near, 1e9, dnn)
for s in SKIP:
    M.mesh.setAlgorithm(2, s, 1)   # MeshAdapt on that face
PROX = float(os.environ.get("PROX", 0))   # 1.5 tried: 1.74 M nodes (too many); off by default since u666_geo fuses each region
prox_fields, s = [], 0.1
while PROX > 0 and s < H:   # size bins 0.1, 0.2, 0.4 ...: local balls (Distance+Threshold), not along whole extruded edges
    pts = [t for t, d in zip(vt, dnn) if s <= max(0.1, PROX * d) < 2 * s]
    if pts and not AIR:
        dist_p = M.mesh.field.add("Distance")
        M.mesh.field.setNumbers(dist_p, "PointsList", pts)
        th_p = M.mesh.field.add("Threshold")
        M.mesh.field.setNumber(th_p, "InField", dist_p)
        for k, v in dict(SizeMin=s, SizeMax=H, DistMin=s, DistMax=4 * H).items():
            M.mesh.field.setNumber(th_p, k, v)
        prox_fields.append(th_p)
        print("proximity bin %.2f mm: %d vertices" % (s, len(pts)), flush=True)
    s *= 2
gmsh.option.setNumber("Mesh.MeshSizeMax", 40.0 if AIR else H * 1.2)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", float(os.environ.get("CURV", 0)))   # 10 -> crossing 1D edges on CAD B-spline faces (housing 1428 hung)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
fields, cfield = list(prox_fields), {}
# local refinement boxes "x0,y0,z0,x1,y1,z1,size;...". Default: rear bearing bore r 8.5 vs shaft r 8.47 at z -20.2
# (0.03 mm inair ring): chords at 1.5 mm cut across the other circle (u666_surfcheck: 108 crossings) -> PLC in inair
for bx in os.environ.get("REFINE", "-10,-10,-20.6,10,10,-19.8,0.3").split(";"):
    if bx and not AIR:
        v = list(map(float, bx.split(",")))
        fb = M.mesh.field.add("Box")
        for k, x in zip(("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax", "VIn"), v):
            M.mesh.field.setNumber(fb, k, x)
        M.mesh.field.setNumber(fb, "VOut", 1e9)
        fields.append(fb)
if AIR:
    dist = M.mesh.field.add("Distance")
    M.mesh.field.setNumbers(dist, "SurfacesList", mot)
    th = M.mesh.field.add("Threshold")
    M.mesh.field.setNumber(th, "InField", dist)
    for k, v in dict(SizeMin=float(os.environ.get("AIR_SKIN", 3.0)), SizeMax=40.0, DistMin=4.0, DistMax=250.0).items():
        M.mesh.field.setNumber(th, k, v)
    fields.append(th)
else:
    for n, ts in regions.items():
        f = M.mesh.field.add("Constant")
        cfield[n] = f
        M.mesh.field.setNumbers(f, "VolumesList", ts)
        M.mesh.field.setNumber(f, "VIn", SIZE.get(n, H))
        M.mesh.field.setNumber(f, "VOut", 1e9)
        fields.append(f)
fmin = M.mesh.field.add("Min")
M.mesh.field.setNumbers(fmin, "FieldsList", fields)
M.mesh.field.setAsBackgroundMesh(fmin)
gmsh.option.setNumber("Mesh.Algorithm", 6)
gmsh.option.setNumber("Mesh.Algorithm3D", int(os.environ.get("ALG3D", 1)))
gmsh.option.setNumber("General.NumThreads", int(os.environ.get("NTHREADS", 1)))
gmsh.option.setNumber("Mesh.Optimize", 1)
gmsh.option.setNumber("Mesh.OptimizeNetgen", int(os.environ.get("NETGEN", 1 if GRP else 0)))   # group route: fewer skew cells (checkMesh)
gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", float(os.environ.get("FACET_TOL", 0.01)))   # gasket-rim slivers: 0.065 deg folds
import re
gmsh.logger.start()
comp = set()
for it in range(60):   # sliver faces (CAD fillets at the terminal-box rim, z -85) fail "1D mesh not a closed loop":
    try:               # mesh each failing face as a compound with its neighbours on the same volume pair, retry
        M.mesh.generate(2)
        break
    except Exception:
        log, cur = gmsh.logger.get(), None
        gmsh.logger.stop(); gmsh.logger.start()
        for l in log:
            m = re.search(r"Meshing surface (\d+)", l)
            if m:
                cur = int(m.group(1))
            elif l.startswith("Error"):
                break
        if cur is None or cur in comp:
            raise
        up = sorted(M.getAdjacencies(2, cur)[0])
        if len(up) == 1 and not AIR:   # skin face (air removed): defeature it instead
            v = up[0]
            print("2D failed on skin face", cur, M.getType(2, cur), "area %.4f" % occ.getMass(2, cur),
                  [round(x, 2) for x in M.getBoundingBox(2, cur)], flush=True)
            try:
                try:
                    new = [t for d, t in occ.defeature([v], [cur]) if d == 3]
                except Exception as e:   # e.g. inverted cone on the fused cap: heal that volume only
                    print("  defeature failed (%s): healing volume %d" % (e, v), flush=True)
                    s0 = sum(1 for _, s in M.getEntities(2) if len(M.getAdjacencies(2, s)[0]) == 2)
                    new = [t for d, t in occ.healShapes([(3, v)], 1e-3, True, True, True, False, False) if d == 3]
                    occ.synchronize()
                    print("  healed; shared faces", s0, "->",
                          sum(1 for _, s in M.getEntities(2) if len(M.getAdjacencies(2, s)[0]) == 2), flush=True)
                occ.synchronize()
                for ts in regions.values():
                    if v in ts:
                        ts[ts.index(v):ts.index(v) + 1] = new
                M.removePhysicalGroups()   # physical groups and size fields follow the new tag
                for n, ts in regions.items():
                    M.addPhysicalGroup(3, ts, name=n)
                    if n in cfield:
                        M.mesh.field.setNumbers(cfield[n], "VolumesList", ts)
                print("  defeatured -> volume", new, flush=True)
                comp.add(cur)
                M.mesh.clear()
                continue
            except Exception as e:
                print("  defeature failed:", e, flush=True)
        reg = {u: n for n, ts in regions.items() for u in ts}
        if len(up) == 2 and reg.get(up[0]) == reg.get(up[1]) and not AIR:   # internal same-region face: fuse
            print("2D failed on internal %s face" % reg[up[0]], cur, M.getType(2, cur), "area %.2f" % occ.getMass(2, cur),
                  [round(x, 2) for x in M.getBoundingBox(2, cur)], flush=True)
            try:
                new = [t for d, t in occ.fuse([(3, up[0])], [(3, up[1])])[0] if d == 3]
                occ.synchronize()
                ts = regions[reg[up[0]]]
                ts[:] = [t for t in ts if t not in up] + new
                M.removePhysicalGroups()
                for n, ts in regions.items():
                    M.addPhysicalGroup(3, ts, name=n)
                    if n in cfield:
                        M.mesh.field.setNumbers(cfield[n], "VolumesList", ts)
                print("  fused", up, "->", new, flush=True)
                comp.add(cur)
                M.mesh.clear()
                continue
            except Exception as e:
                print("  fuse failed:", e, flush=True)
        grp = {cur} |{f for _, c in M.getBoundary([(2, cur)], oriented=False) for f in M.getAdjacencies(1, abs(c))[0]
                       if f not in comp and sorted(M.getAdjacencies(2, f)[0]) == up}
        print("compound", it, cur, sorted(grp), flush=True)
        M.mesh.setCompound(2, sorted(grp))
        comp |= grp
        M.mesh.clear()
# surfaces with invalid (flipped) triangles (housing fin B-spline faces, cap torus) -> "PLC Error" in 3D:
# re-mesh them with MeshAdapt, then with a finer size on their points
fixed = {}
for it in range(4):
    bad = sorted({int(m.group(1)) for l in gmsh.logger.get() for m in [re.search(r"remain invalid in surface (\d+)", l)] if m})
    gmsh.logger.stop(); gmsh.logger.start()
    if not bad:
        break
    print("invalid triangles, pass", it, "surfaces", bad, flush=True)
    for s in bad:
        fixed[s] = fixed.get(s, 0) + 1
        M.mesh.setAlgorithm(2, s, 1)
        if fixed[s] > 1:
            M.mesh.setSize(M.getBoundary([(2, s)], oriented=False, recursive=True), H / 2 ** fixed[s])
    M.mesh.clear()
    M.mesh.generate(2)
if "--2d" in sys.argv:   # surface mesh only, for scripts/u666_surfcheck.py (triangle intersections -> PLC location)
    gmsh.option.setNumber("Mesh.SaveAll", 1)
    gmsh.write(os.path.join(OUT, "u666_2d.msh"))
    sys.exit(0)
if "--stl" in sys.argv:   # snappyHexMesh input (u666_snappy.sh): 2D only, one closed STL per region (mm) + the skin
    d = os.path.join(OUT, "stl")
    os.makedirs(d, exist_ok=True)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.option.setNumber("Mesh.StlOneSolidPerSurface", 0)
    allv = [(3, t) for ts in regions.values() for t in ts]
    for n, dts in list({n: [(3, t) for t in ts] for n, ts in regions.items()}.items()) + [("skin", allv)]:
        fs = sorted({abs(t) for _, t in M.getBoundary(dts, combined=True, oriented=False)})
        M.removePhysicalGroups()
        M.addPhysicalGroup(2, fs, name=n)
        gmsh.write(os.path.join(d, n + ".stl"))
        print("stl", n, "faces", len(fs), flush=True)
    json.dump(info, open(os.path.join(d, "volumes.json"), "w"), indent=1)
    print("stl done")
    sys.exit(0)
try:
    M.mesh.generate(3)
except Exception as e:
    bad = [t for d, t in M.getEntities(2) if len(M.mesh.getElements(2, t)[1]) == 0]
    print("FAILED:", e, "- surfaces without mesh:", bad[:20])
    for t in bad[:5]:
        print(t, M.getBoundingBox(2, t), M.getAdjacencies(2, t)[0])
    if os.environ.get("DIAG", "0") == "1":   # per volume: each volume + its boundary visible (recursive), 3D alone
        gmsh.option.setNumber("Mesh.MeshOnlyVisible", 1)
        reg = {u: n for n, ts in regions.items() for u in ts}
        for _, v in M.getEntities(3):
            M.setVisibility(M.getEntities(), 0)
            M.setVisibility([(3, v)], 1, recursive=True)
            try:
                M.mesh.generate(3)
                nt = sum(len(e) for e in M.mesh.getElements(3, v)[1])
                print("DIAG ok   vol", v, reg.get(v), "tets", nt, flush=True)
            except Exception as e2:
                print("DIAG FAIL vol", v, reg.get(v), [round(x, 2) for x in M.getBoundingBox(3, v)], str(e2)[:80], flush=True)
            M.mesh.clear([(3, v)])
    raise
if GRP:   # patches. Mixed faces: each triangle -> label of the nearest ORIGINAL face (brep reloaded as model "ref")
    if mixed:
        cur = M.getCurrent()
        tris = []
        for f, ls in mixed:
            nt, nc, _ = M.mesh.getNodes(2, f, includeBoundary=True)
            X = dict(zip(nt, np.array(nc).reshape(-1, 3)))
            _, et, en = M.mesh.getElements(2, f)
            conn = np.array(en[0]).reshape(-1, 3)
            tris.append((f, ls, et[0], conn, np.array([[X[n] for n in t] for t in conn]).mean(1)))
        # label = nearest PARTNER patch triangle (partner group meshed first: u666_g_<nb>.msh, patch <nb>_to_<GRP>);
        # "outside" wins when no partner triangle lies within OUT_TOL (0.5 mm). Exact up to one triangle at borders.
        from scipy.spatial import cKDTree
        trees = {}
        for l in {l for _, ls, *_ in tris for l in ls if l != "outside"}:
            nb = l.split("_to_")[1]
            gmsh.model.add("ref_" + nb)
            gmsh.merge(os.path.join(OUT, "u666_g_%s.msh" % nb))
            pc = []
            nt, nc, _ = gmsh.model.mesh.getNodes()
            X = np.zeros((int(nt.max()) + 1, 3))
            X[nt.astype(int)] = np.array(nc).reshape(-1, 3)
            for d2, pg in gmsh.model.getPhysicalGroups(2):
                if gmsh.model.getPhysicalName(d2, pg) == nb + "_to_" + GRP:
                    for e in gmsh.model.getEntitiesForPhysicalGroup(2, pg):
                        _, _, en = gmsh.model.mesh.getElements(2, e)
                        pc += list(X[np.array(en[0]).astype(int).reshape(-1, 3)])
            pc = np.array(pc)
            trees[l] = (cKDTree(pc.mean(1)), pc)
            gmsh.model.remove()
            print("partner", l, len(pc), "triangles", flush=True)
        best = []
        for f, ls, et, conn, cen in tris:
            def pdist(l):   # distance from each centroid to the partner triangles (12 nearest, exact point-triangle)
                if l not in trees:
                    return np.full(len(cen), float(os.environ.get("OUT_TOL", 0.5)))
                tr, P = trees[l]
                _, ii = tr.query(cen, k=min(12, len(P)))
                ii = ii.reshape(len(cen), -1)
                a, b, c = P[ii, 0], P[ii, 1], P[ii, 2]
                q = cen[:, None, :]
                n = np.cross(b - a, c - a)
                n = n / np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-30)
                h = ((q - a) * n).sum(2)
                pr = q - h[..., None] * n
                ins = np.ones(h.shape, bool)
                for u, v in ((a, b), (b, c), (c, a)):
                    ins &= (np.cross(v - u, pr - u) * n).sum(2) >= -1e-9
                edge = np.minimum(np.linalg.norm(q - a, axis=2), np.minimum(np.linalg.norm(q - b, axis=2), np.linalg.norm(q - c, axis=2)))
                return np.where(ins, np.abs(h), edge).min(1)
            d = np.array([pdist(l) for l in ls]).T
            best.append(d.argmin(1))
            print("mixed face", f, {l: int((d.argmin(1) == j).sum()) for j, l in enumerate(ls)}, flush=True)
        gmsh.model.setCurrent(cur)
        for (f, ls, et, conn, cen), bj in zip(tris, best):
            M.mesh.removeElements(2, f)
            for j, l in enumerate(ls):
                if (bj == j).any():
                    s2 = M.addDiscreteEntity(2)
                    M.mesh.addElementsByType(s2, 2, [], conn[bj == j].ravel().tolist())
                    pat.setdefault(l, []).append(s2)
    for p, fs in sorted(pat.items()):
        M.addPhysicalGroup(2, fs, name=p)
        print("  patch %-24s faces %5d" % (p, len(fs)), flush=True)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.SaveAll", 0)
name = "u666_air" if AIR else ("u666_g_" + GRP if GRP else "u666_solids")
gmsh.write(os.path.join(OUT, name + ".msh"))
_, et, _ = M.mesh.getElements(3)
info["_cells"] = int(sum(len(e) for e in et))
json.dump(info, open(os.path.join(OUT, name + "_regions.json"), "w"), indent=1)
print("tets:", info["_cells"])

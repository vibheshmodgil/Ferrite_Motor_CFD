"""U666 pre-pass: defeature the kept CAD parts of mesh/u666/subset.brep BEFORE the fragment (u666_geo.py --df).

    .venv/Scripts/python -I scripts/u666_defeature.py [--inv]   (--inv: inventory only)
-> mesh/u666/subset_df.brep (same solid order/tags as subset.brep, so subset.json stays valid),
   results/u666/defeature_inventory.md, results/u666/defeature.json
Removed (one part per occ.defeature call, small face lists): fillets/rounds r < 2 mm (torus minor r, sphere, partial
cylinder), chamfers < 2 mm (cone strips), holes d < 3 mm (full cylinders whose axis lies outside the solid).
Threads: none modelled in the CAD (Creo cosmetic) -> helical B-spline faces are only reported.
Wedges (slot opening) and the lip seal (its lips are cones/tori) are kept exact. Kept exact by the thresholds: fits, bearing seats, fins, main skin (large r / plane). Stacks, magnets, liner are rebuilt
by u666_geo.py and are not touched; 74 (gasket) and 114 (terminal cap) are replaced there by prisms -> not touched.
"""
import gmsh, json, math, os, sys, time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "mesh", "u666")
RES = os.path.join(ROOT, "results", "u666")
SUB = json.load(open(os.path.join(OUT, "subset.json")))
R_FIL, W_CH, D_HOLE = 1.95, 2.0, 3.0      # 1.95: 2.0 mm fin-root fillets stay (CAD r 1.999..)
BLEND = 0.55 * math.pi                    # a blend spans <= ~90 deg; half / full cylinders and tori are holes, rods, O-rings
PARTS = [(k, t) for k in ("shaft", "housing", "endcaps", "screws") for t in SUB[k] if t not in (74, 114)]
# ponytail: housing 39 (714 cm3, 870 B-spline faces) took 200 s and then > 20 min per 15-face call -> skipped by default
SKIP = {int(x) for x in os.environ.get("DF_SKIP", "39").split(",") if x}
CHUNK = int(os.environ.get("CHUNK", 400))   # faces per call; per-call cost ~ solid size (64: 408 s for 15 faces) -> big chunk, bisect on failure
t0 = time.time()
step = lambda m: print("%-40s %6.0f s" % (m, time.time() - t0), flush=True)

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
occ, M = gmsh.model.occ, gmsh.model
occ.importShapes(os.path.join(OUT, "subset.brep"))
occ.synchronize()
step("loaded")


def kmax(f):
    """max |principal curvature| at the parametric centre (and that point, its normal)."""
    b = M.getParametrizationBounds(2, f)
    uv = [0.5 * (b[0][0] + b[1][0]), 0.5 * (b[0][1] + b[1][1])]
    k1, k2, _, _ = M.getPrincipalCurvatures(f, uv)
    return max(abs(k1[0]), abs(k2[0])), M.getValue(2, f, uv), M.getNormal(f, uv), b


def classify(vol, f):
    typ = M.getType(2, f)
    a = occ.getMass(2, f)
    try:
        k, p, n, b = kmax(f)
    except Exception:
        return None
    r = 1 / k if k > 1e-9 else 1e9
    if typ == "Torus":                                         # v = tube angle
        return ("fillet", r, a) if r < R_FIL and abs(b[1][1] - b[0][1]) <= BLEND else None
    if typ == "Sphere":
        return ("round", r, a) if r < R_FIL else None
    if typ == "Cylinder":
        span = abs(b[1][0] - b[0][0])                            # u = angle on an OCC cylinder
        if span <= BLEND:
            return ("fillet", r, a) if r < R_FIL else None
        if 2 * r >= D_HOLE:
            return None
        for s in (1, -1):                                       # axis point: centre side of the normal
            c = [p[i] + s * n[i] * r for i in range(3)]
            q = M.getClosestPoint(2, f, c)[0]
            if abs(math.dist(q, c) - r) < 1e-3 * max(r, 1):
                return ("hole", r, a) if not M.isInside(3, vol, c) else None
        return None
    if typ == "Cone":
        per = sum(occ.getMass(1, abs(c)) for _, c in M.getBoundary([(2, f)], oriented=False))
        w = 2 * a / per if per > 0 else 1e9                       # strip width of a narrow face
        return ("chamfer", w, a) if w < W_CH else None
    return None


inv, log = {}, {}
for name, t in PARTS:
    rows = []
    for _, f in M.getBoundary([(3, t)], oriented=False):
        c = classify(t, abs(f))
        if c:
            rows.append((abs(f),) + c)
    inv[t] = (name, rows)
step("inventory")

# ---- inventory table
os.makedirs(RES, exist_ok=True)
with open(os.path.join(RES, "defeature_inventory.md"), "w") as fo:
    fo.write("# U666 defeature inventory (subset.brep, thresholds fillet r < %.0f mm, chamfer < %.0f mm, hole d < %.0f mm)\n\n"
             % (R_FIL, W_CH, D_HOLE))
    fo.write("Threads: none modelled in the CAD (cosmetic in Creo). Gasket 74 / terminal cap 114: replaced by prisms in u666_geo.py.\n\n")
    fo.write("| part | tag | V cm3 | fillet/round n | r min-max mm | area mm2 | chamfer n | w min-max mm | area mm2 | hole n | d min-max mm | area mm2 |\n")
    fo.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for t, (name, rows) in inv.items():
        cells = []
        for kinds in (("fillet", "round"), ("chamfer",), ("hole",)):
            rs = [r for r in rows if r[1] in kinds]
            if not rs:
                cells += ["0", "-", "0"]
                continue
            sz = [r[2] * (2 if kinds == ("hole",) else 1) for r in rs]
            cells += [str(len(rs)), "%.2f-%.2f" % (min(sz), max(sz)), "%.0f" % sum(r[3] for r in rs)]
        fo.write("| %s | %d | %.1f | %s |\n" % (name, t, occ.getMass(3, t) / 1e3, " | ".join(cells)))
step("inventory written")
if "--inv" in sys.argv:
    sys.exit(0)

# ---- defeature, one part per call, CHUNK faces at a time; a failing chunk is retried face by face.
# Face tags may change after each call -> re-classify the current solid every round; failures are keyed by geometry.
key = lambda f: (M.getType(2, f), round(occ.getMass(2, f), 2), tuple(round(x, 2) for x in M.getBoundingBox(2, f)))
new = {}
for t, (name, rows) in inv.items():
    if not rows or t in SKIP:
        log[t] = dict(part=name, faces=len(rows), removed=0, skipped=t in SKIP)
        continue
    v0, a0 = occ.getMass(3, t), sum(r[3] for r in rows)
    cur, done, bad, n = t, 0, set(), CHUNK
    for _ in range(400):
        todo = [f for _, f in M.getBoundary([(3, cur)], oriented=False) if classify(cur, abs(f))]
        todo = [abs(f) for f in todo if key(abs(f)) not in bad]
        if not todo:
            break
        ch = todo[:n]                                            # a failed chunk stays first -> bisected
        vb, kch, tc = occ.getMass(3, cur), [key(f) for f in ch], time.time()
        bk, nt = occ.copy([(3, cur)]), []                        # a failed call can delete the input solid
        try:
            out = occ.defeature([cur], ch, removeVolume=True)
            occ.synchronize()
            nt = [x for d, x in out if d == 3]
            assert len(nt) == 1 and abs(occ.getMass(3, nt[0]) - vb) < 0.05 * vb
            left = [f for _, f in M.getBoundary([(3, nt[0])], oriented=False) if classify(nt[0], abs(f))]
            if len(left) >= len(todo):                           # no progress: OCC kept the faces
                bad |= set(kch)
            cur, done = nt[0], done + max(0, len(todo) - len(left))
            occ.remove(bk, recursive=True)
            occ.synchronize()
        except Exception:
            occ.synchronize()
            ex = M.getEntities(3)
            occ.remove([(3, x) for x in nt if (3, x) in ex and x != cur], recursive=True)   # rejected result
            if (3, cur) in M.getEntities(3):
                occ.remove(bk, recursive=True)
            else:
                cur = bk[0][1]
            occ.synchronize()
            if len(ch) == 1:
                bad.add(kch[0])
                n = CHUNK
            else:
                n = len(ch) // 2
        print("  %d: %d faces left, chunk %d, bad %d, %.0f s" % (t, len(todo), len(ch), len(bad), time.time() - tc), flush=True)
    if cur != t:
        new[t] = cur
    log[t] = dict(part=name, faces=len(rows), removed=done, failed=len(bad), area_mm2=round(a0, 1),
                  dV_mm3=round(occ.getMass(3, cur) - v0, 1))
    step("%s %d: %d/%d faces, %d failed, dV %.1f mm3" % (name, t, done, len(rows), len(bad), log[t]["dV_mm3"]))

# ---- keep the solid order of subset.brep (a reload renumbers 1..N in tag order): copy all in order, export only them
order = range(1, 1 + sum(len(v) for v in SUB.values()))
src = [new.get(t, t) for t in order]
cp = [occ.copy([(3, s)])[0][1] for s in src]
occ.synchronize()                                              # occ.remove is O(N^2) here: export only the copies
M.setVisibility(M.getEntities(), 0)
M.setVisibility([(3, c) for c in cp], 1, recursive=True)
gmsh.option.setNumber("Geometry.OCCExportOnlyVisible", 1)
gmsh.write(os.path.join(OUT, "subset_df.brep"))
json.dump(log, open(os.path.join(RES, "defeature.json"), "w"), indent=1)
step("written subset_df.brep")

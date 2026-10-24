"""U666: fuse the pieces of each region of u666_geo.py's output and glue everything again (conformal), for gmsh.

    .venv/Scripts/python -I scripts/u666_fuse.py     mesh/u666/u666_geo_raw.brep(.json) -> mesh/u666/u666_geo.brep(.json)

Why: the priority fragment leaves internal same-region faces (gasket/cap/cover slivers in the housing, shaft faces from
lower-priority overlaps). gmsh then gives crossing 1D edges, overlapping facets or "PLC Error" in 3D.
A region whose fuse fails (OCC) keeps its pieces; the log says which.
"""
import gmsh, json, os, sys, time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh", "u666")
SKIP = set(os.environ.get("FUSE_SKIP", "air,endcaps,housing").split(","))   # housing: OCC fuse fails ("Courbes non jointives"); one-by-one lost 370 cm3 -> never; endcaps: cap+nut fuse left a dangling internal face (r 15.8) -> PLC error
t0 = time.time()
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
occ, M = gmsh.model.occ, gmsh.model
occ.importShapes(os.path.join(OUT, "u666_geo_raw.brep"))
occ.synchronize()
R = json.load(open(os.path.join(OUT, "u666_geo_raw.brep.json")))
rank = {t: k + 1 for k, t in enumerate(sorted(t for ts in R.values() for t in ts))}
R = {n: [rank[t] for t in ts] for n, ts in R.items()}
assert {t for ts in R.values() for t in ts} == {t for _, t in M.getEntities(3)}
vol = lambda ts: sum(occ.getMass(3, t) for t in ts) / 1e3
v0 = {n: vol(ts) for n, ts in R.items()}
fused = {}
for n, ts in R.items():
    if len(ts) == 1 or n in SKIP:
        fused[n] = ts
        continue
    try:
        o, _ = occ.fuse([(3, ts[0])], [(3, t) for t in ts[1:]])
        fused[n] = [t for d, t in o if d == 3]
    except Exception as e:   # one-by-one: pieces that break the fuse stay separate
        print("fuse FAILED", n, e, "- trying one by one", flush=True)
        acc, alone = [ts[0]], []
        for t in ts[1:]:
            try:
                o, _ = occ.fuse([(3, a) for a in acc], [(3, t)])
                acc = [v for d, v in o if d == 3]
            except Exception:
                alone.append(t)
        fused[n] = acc + alone
        print("  %s: %d pieces would not fuse" % (n, len(alone)), flush=True)
    print("%-8s %4d -> %4d pieces  %5.0f s" % (n, len(ts), len(fused[n]), time.time() - t0), flush=True)
ins = [(n, t) for n, ts in fused.items() for t in ts]
o, omap = occ.fragment([(3, t) for _, t in ins], [])
occ.synchronize()
regions, owner = {}, {}
for (n, _), ch in zip(ins, omap):
    for d, t in ch:
        if d == 3 and t not in owner:
            owner[t] = n
            regions.setdefault(n, []).append(t)
assert set(owner) == {t for _, t in M.getEntities(3)}, "fragment left unowned volumes"
print("refragment %.0f s" % (time.time() - t0), flush=True)
for n, ts in regions.items():
    print("%-8s pieces %4d  %10.2f cm3 (was %10.2f)" % (n, len(ts), vol(ts), v0[n]), flush=True)
leak = 0.0
for t in regions["inair"]:
    for _, f in M.getBoundary([(3, t)], oriented=False):
        if any(owner.get(u) == "air" for u in M.getAdjacencies(2, abs(f))[0]):
            leak += occ.getMass(2, abs(f))
print("inair-air contact area mm2: %.1f" % leak)
gmsh.write(os.path.join(OUT, "u666_geo.brep"))
json.dump({n: sorted(ts) for n, ts in regions.items()}, open(os.path.join(OUT, "u666_geo.brep.json"), "w"))
print("done %.0f s" % (time.time() - t0))
dang = [abs(f) for n, ts in regions.items() if n != "air" for t in ts for _, f in M.getBoundary([(3, t)], oriented=False)
        if len(M.getAdjacencies(2, abs(f))[0]) == 1 and owner.get(M.getAdjacencies(2, abs(f))[0][0]) != "air"
        and any(abs(M.getBoundingBox(2, abs(f))[i]) < 290 for i in range(6))]
print("single-volume faces (dangling inside a region, or skin after the air is removed):", len(set(dang)))

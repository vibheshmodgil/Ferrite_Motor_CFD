"""Save the solids the U666 thermal model needs from the 599-solid BREP cache into mesh/u666/subset.brep (once).

    .venv/Scripts/python -I scripts/u666_subset.py [--with-winding]
gmsh's occ.remove is O(N^2) on this model (stalled > 30 min), so nothing is removed: the kept solids are made
visible and exported with Geometry.OCCExportOnlyVisible. Writes subset.brep + subset.json {name: [tags]}.
"""
import gmsh, json, os, sys, time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mesh", "u666")
INV = json.load(open(os.path.join(OUT, "inv.json")))
nm = lambda r: r["name"].split("/")[-1]
t0 = time.time()
step = lambda msg: print("%-28s %6.0f s" % (msg, time.time() - t0), flush=True)
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
occ, M = gmsh.model.occ, gmsh.model
occ.importShapes(os.path.join(OUT, "u666.brep"))
occ.synchronize()
step("brep loaded")
PARTS = {   # name -> inventory name prefixes
    "lam_s": ["KE250030_1"], "lam_r": ["KE250110_1"], "magnet": ["KE250130"], "shaft": ["GE250300"],
    "housing": ["KE250089", "KE250269", "KE250179", "KE250380", "KE250200", "KE250300", "KE250280", "KE240750"],
    "endcaps": ["KE250150", "KE250370", "KE250320"], "seal": ["K2200050"], "wedge": ["KE250530"],
    "liner": ["KE250520"], "wcad": ["KE250510"],
    "screws": ["M1200", "KE200090", "420001", "420051"],                   # fill their holes (metal)
    "cable": ["GE250410", "GE250420", "GE250430", "GE250480", "GE250340"]}  # cut to the gland wall -> plug
sel = {k: [r for r in INV if any(nm(r).startswith(p) for p in v)] for k, v in PARTS.items()}
sel["lam_s"] = sel["lam_s"][:1]
sel["lam_r"] = sel["lam_r"][:1]
z1 = min(r["bb"][2] for r in sel["magnet"])
sel["magnet"] = [r for r in sel["magnet"] if abs(r["bb"][2] - z1) < 0.05]       # first axial segment (18)
if "--with-winding" not in sys.argv:
    sel["liner"], sel["wcad"] = sel["liner"][:1], []
keep = {r["tag"] for v in sel.values() for r in v}
# no removal (O(N^2) in gmsh): hide all, show the kept solids, export only the visible ones
M.setVisibility(M.getEntities(), 0)
M.setVisibility([(3, t) for t in keep], 1, recursive=True)
gmsh.option.setNumber("Geometry.OCCExportOnlyVisible", 1)
step("visibility set")
TAG = "subset_w" if "--with-winding" in sys.argv else "subset"
gmsh.write(os.path.join(OUT, TAG + ".brep"))
rank = {t: k + 1 for k, t in enumerate(sorted(keep))}      # reload renumbers 1..N in tag order
json.dump({k: [rank[r["tag"]] for r in v] for k, v in sel.items()}, open(os.path.join(OUT, TAG + ".json"), "w"), indent=0)
step("written")

"""Export decimated boundary surfaces + temperatures per part for the site's 3D viewer (viewer3d.html).

    .venv/Scripts/python -I scripts/export_viewer.py [duty1 duty2 ...]     (default: every point with fields)

Reads the reconstructed OpenFOAM cases in WSL (~/cfd/<lp>, ~/cfd/det_<lp>) directly over \\wsl.localhost, one region and one
time at a time; nothing is written in WSL. Surface temperature = adjacent cell value (like foamToVTK -nearCellValue). Writes
Report/Design9795_site/assets/viewer/{geom_<model>.js, temp_<lp>_<model>.js, manifest.js}; the .js files wrap the binary
(base64) so the page also works from file:// (browsers block fetch() of local .bin files). Existing manifest entries are kept,
so a new point (duty3, duty5) is added with one command; reconstruct its time directories first.
Aborts if C: < 9 GB free or available RAM < 1.5 GB.
"""
import base64, ctypes, json, os, re, shutil, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_report_duty as M

WSL = r"\\wsl.localhost\Ubuntu-24.04\home\cfd\cfd"
OUTD = os.path.join(M.OUT, "Design9795_site", "assets", "viewer")
TOTAL_V = 150_000           # vertex budget per model
K = 273.15
# key, label, region, copper zones (detailed only), (monitor region, max file, mean file)
BASE = [("housing", "Housing", "housing", None, ("housing", "T_housing", "Tavg_housing")),
        ("stator", "Stator", "stator", None, ("stator", "T_stator", None)),
        ("winding", "Winding", "winding", None, ("winding", "T_winding", "Tavg_winding")),
        ("rotor", "Rotor", "rotor", None, ("rotor", "T_rotor", None)),
        ("magnets", "Magnets", "magnets", None, ("magnets", "T_magnets", "Tavg_magnets")),
        ("shaft", "Shaft", "shaft", None, ("shaft", "T_shaft", None)),
        ("bearings", "Bearings", "bearings", None, ("bearings", "T_bearings", None))]
DETP = [BASE[0], BASE[1],
        ("winding", "Coil", "copper", ("coil",), ("copper", "T_coil", "Tavg_coil")),
        ("busbar", "Busbar", "copper", ("busbar",), ("copper", "T_busbar", None)),
        ("strap", "Strap", "copper", ("strap",), ("copper", "T_strap", None)),
        ("tbar", "T-bar", "copper", ("tbar",), ("copper", "T_tbar", None)),
        ("resin", "Resin", "resin", None, ("resin", "T_resin", None)),
        ("bobbin", "Bobbin", "bobbin", None, ("bobbin", "T_bobbin", None))] + BASE[3:]


def guard():
    class MS(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in
                    ("tot", "avail", "tpf", "apf", "tv", "av", "aev")]
    m = MS(); m.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    free = shutil.disk_usage("C:\\").free
    if free < 9e9 or m.avail < 1.5e9:
        sys.exit(f"abort: C: {free/1e9:.1f} GB free, RAM {m.avail/1e9:.2f} GB available")


# ---------------------------------------------------------------- OpenFOAM binary readers (label 32, scalar 64)
def body(path):
    b = open(path, "rb").read()
    return b, b.index(b"}", b.index(b"FoamFile")) + 1


def blist(b, pos, dt, ncomp=1, key=None):
    """Next 'N (' binary list from pos (optionally after key); returns (array, end position). 'uniform v' -> (float, end)."""
    if key:
        pos = b.index(key, pos) + len(key)
        mu = re.compile(rb"\s*uniform\s+([-\d.eE+]+)").match(b, pos)
        if mu:
            return float(mu[1]), mu.end()
    m = re.compile(rb"(\d+)\s*\(").search(b, pos)
    n = int(m[1]); s = m.end()
    if b"format      ascii" in b[:600]:      # ascii list: numbers up to the closing ")" (vectors are "(x y z)" lines)
        e = b.index(b"\n)", s) if ncomp > 1 else b.index(b")", s)
        a = np.fromstring(b[s:e].translate(PAREN), dtype=np.float64 if dt.endswith("f8") else np.int64, sep=" ")
        a = a.astype(dt)
    else:
        e = s + n * ncomp * np.dtype(dt).itemsize
        a = np.frombuffer(b, dt, n * ncomp, s)
    return (a.reshape(n, ncomp) if ncomp > 1 else a), e + 1


PAREN = bytes.maketrans(b"()", b"  ")


def faces(path):
    """faceList (ascii 'n(a b c)') or faceCompactList (binary offsets + labels) -> offsets, labels."""
    b, p = body(path)
    if b"faceCompactList" in b[:600]:
        off, p = blist(b, p, "<i4"); lab, _ = blist(b, p, "<i4")
        return off, lab
    m = re.compile(rb"(\d+)\s*\(").search(b, p)
    a = np.fromstring(b[m.end():b.rindex(b"\n)")].translate(PAREN), dtype=np.int64, sep=" ").astype(np.int32)
    if (a[::4] == 3).all() and len(a) == 4 * int(m[1]):          # all triangles (tet mesh)
        return np.arange(0, 3 * int(m[1]) + 1, 3, dtype=np.int32), a.reshape(-1, 4)[:, 1:].ravel()
    off, lab, i = [0], [], 0                                      # ponytail: python loop for mixed polygons, slow only on huge hex meshes
    while i < len(a):
        k = a[i]; lab.append(a[i + 1:i + 1 + k]); off.append(off[-1] + k); i += k + 1
    return np.array(off, np.int32), np.concatenate(lab)


def mesh(case, region):
    d = os.path.join(case, "constant", region, "polyMesh")
    b, p = body(os.path.join(d, "points")); pts, _ = blist(b, p, "<f8", 3)
    off, lab = faces(os.path.join(d, "faces"))
    b, p = body(os.path.join(d, "owner")); own, _ = blist(b, p, "<i4")
    bnd = open(os.path.join(d, "boundary"), encoding="latin-1").read()
    f0 = min(int(x) for x in re.findall(r"startFace\s+(\d+);", bnd))
    zones = {}
    if os.path.exists(os.path.join(d, "cellZones")):
        b, p = body(os.path.join(d, "cellZones"))
        for m in re.finditer(rb"\n(\w+)\s*\{\s*type\s+cellZone;\s*cellLabels\s+List<label>", b):
            zones[m[1].decode()], _ = blist(b, m.end(), "<i4")
    return pts, off, lab, own, f0, zones


def cellT(case, t, region):
    b, p = body(os.path.join(case, t, region, "T"))
    v, _ = blist(b, p, "<f8", key=b"internalField")
    return v


# ---------------------------------------------------------------- surface + vertex-cluster decimation
def surface(pts, off, lab, own, f0, sel=None):
    """Boundary faces (optionally only those whose owner cell is in sel) -> (face ids, polygon vertex lists)."""
    fid = np.arange(f0, len(off) - 1)
    if sel is not None:
        fid = fid[np.isin(own[fid], sel)]
    return fid


def decimate(pts, off, lab, fid, target):
    """Vertex clustering on a grid sized to ~target clusters. Returns cluster xyz, triangles, (face, cluster) pairs."""
    n = (off[fid + 1] - off[fid]).astype(np.int64)
    start = np.cumsum(n) - n                        # first slot of each face in the flat face-vertex list
    fv = lab[np.repeat(off[fid], n) + (np.arange(n.sum()) - np.repeat(start, n))]
    used, inv = np.unique(fv, return_inverse=True)
    P = pts[used]
    lo, span = P.min(0), np.ptp(P, 0).max() or 1.0
    h = span / 200
    for _ in range(6):
        cell = np.floor((P - lo) / h).astype(np.int64)
        key = (cell[:, 0] * 1_000_003 + cell[:, 1]) * 1_000_003 + cell[:, 2]
        uk, cid = np.unique(key, return_inverse=True)
        if len(uk) <= target * 1.15 or len(used) <= target:
            break
        h *= (len(uk) / target) ** 0.5
    if len(used) <= target:
        cid, uk = np.arange(len(used)), used
    nc = len(uk)
    w = np.bincount(cid, minlength=nc)
    X = np.stack([np.bincount(cid, P[:, k], nc) for k in range(3)], 1) / w[:, None]
    vc = cid[inv]                                   # cluster of each face-vertex slot
    tri = np.concatenate([np.stack([vc[s], vc[s + k], vc[s + k + 1]], 1)       # polygon fan
                          for k in range(1, int(n.max()) - 1) for s in [start[n > k + 1]]])
    tri = tri[(tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2])]
    _, keep = np.unique(np.sort(tri, 1), axis=0, return_index=True)
    tri = tri[np.sort(keep)]
    pair_f = np.repeat(np.arange(len(fid)), n)      # face index (into fid) of each slot
    return X.astype(np.float32), tri.astype(np.uint32), pair_f, vc, nc


def series(src, mon, grid):
    reg, fmax, fmean = mon
    out = []
    for f in (fmax, fmean):
        if f is None:
            out.append(None); continue
        hs = [M.hist(src, reg, fn=x) for x in (f if isinstance(f, tuple) else (f,))]
        hs = [h for h in hs if h is not None]
        out.append(None if not hs else np.round(np.max([np.interp(grid, h[0], h[1]) for h in hs], 0), 1).tolist())
    return out


def b64js(name, raw):
    open(os.path.join(OUTD, name + ".js"), "w").write(f'VIEWER.got("{name}","{base64.b64encode(raw).decode()}");\n')


def export(lp, model):
    name = lp if model == "baseline" else f"det_{lp}"
    case = os.path.join(WSL, name + "_viz")          # finer-write re-run of the same point, when it exists
    case = case if os.path.isdir(case) else os.path.join(WSL, name)
    print(f"{lp} {model}: {case}")
    src = lp if model == "baseline" else f"detailed/{lp}"
    parts = BASE if model == "baseline" else DETP
    tcut = M.t_stop(src)
    if tcut is None or not os.path.isdir(case):
        print(f"skip {lp} {model}: no monitors or case"); return None
    times = sorted((d for d in os.listdir(case) if re.fullmatch(r"\d+(\.\d+)?", d)
                    and os.path.isdir(os.path.join(case, d, parts[0][2]))), key=float)
    times = [t for t in times if float(t) <= tcut + 1e-6]
    if len(times) < 2:
        print(f"skip {lp} {model}: fewer than 2 saved fields before the cut"); return None
    target = int(np.clip(TOTAL_V / len(parts), 10_000, 30_000))
    geo, P, meta, maps, voff = [], [], [], [], 0
    cache = {}
    for key, label, region, zones, mon in parts:
        guard()
        if region not in cache:
            cache = None; import gc; gc.collect(); guard()
            cache = {region: mesh(case, region)}
        pts, off, lab, own, f0, zd = cache[region]
        sel = np.concatenate([zd[z] for z in zones]) if zones else None
        fid = surface(pts, off, lab, own, f0, sel)
        X, tri, pf, vc, nc = decimate(pts, off, lab, fid, target)
        maps.append((region, own[fid][pf], vc, nc, np.bincount(vc, minlength=nc)))
        meta.append({"key": key, "label": label, "v0": voff, "nv": nc, "nt": len(tri)})
        geo.append((X, tri)); voff += nc
        print(f"  {model} {key}: {len(fid)} faces -> {nc} vertices, {len(tri)} triangles")
    cache = None
    if model not in DONE_GEOM:
        raw = b"".join(X.tobytes() for X, _ in geo) + b"".join(t.tobytes() for _, t in geo)
        b64js(f"geom_{model}", raw); DONE_GEOM.add(model)
    # temperatures per saved time
    vals, stats = [], []
    for t in times:
        guard()
        Tc, row, frame = {}, [], np.empty(voff, np.float32)
        for (region, cells, vc, nc, cnt), m in zip(maps, meta):
            if region not in Tc:
                Tc = {region: cellT(case, t, region)}
            v = Tc[region]
            tv = np.full(len(cells), v) if np.isscalar(v) else v[cells]
            frame[m["v0"]:m["v0"] + nc] = np.bincount(vc, tv, nc) / cnt - K
            row.append([round(float(tv.max()) - K, 1), round(float(tv.mean()) - K, 1)])
        vals.append(frame); stats.append(row)
        print(f"  {lp} {model} t={t}")
    F = np.array(vals)
    lo, hi = 40.0, float(np.ceil(F.max() / 5) * 5)
    b64js(f"temp_{lp}_{model}", np.round((F - lo) / (hi - lo) * 255).clip(0, 255).astype(np.uint8).tobytes())
    tl = float(times[-1])
    grid = np.linspace(0, tl, 241)
    mons = [series(src, mon, grid) for *_, mon in parts]
    for m, (mx, mn) in zip(meta, mons):
        m["mon_max"], m["mon_mean"] = mx, mn
    fixed = max([hi] + [max(mx) for mx, _ in mons if mx])
    return {"lp": lp, "model": model, "name": M.DUTY[lp][0], "rpm": M.DUTY[lp][1], "torque": M.DUTY[lp][2],
            "times": [float(t) for t in times], "t_cut": round(tcut, 1), "q": [lo, hi], "range": [40, float(np.ceil(fixed / 5) * 5)],
            "grid": grid.round(2).tolist(), "parts": meta, "surf_stats": stats, "geom": f"geom_{model}", "temp": f"temp_{lp}_{model}"}


DONE_GEOM = set()

if __name__ == "__main__":
    os.makedirs(OUTD, exist_ok=True)
    mf = os.path.join(OUTD, "manifest.js")
    man = json.loads(open(mf).read().split("=", 1)[1].rstrip().rstrip(";")) if os.path.exists(mf) else {"entries": {}}
    lps = sys.argv[1:] or [lp for lp in M.ORDER if os.path.isdir(os.path.join(WSL, lp))]
    for a in lps:            # "duty4" = both models, "duty4:detailed" = one
        lp, _, only = a.partition(":")
        for model in ([only] if only else ("baseline", "detailed")):
            e = export(lp, model)
            if e:
                man["entries"][f"{lp}/{model}"] = e
                open(mf, "w").write("VIEWER_MANIFEST = " + json.dumps(man, separators=(",", ":")) + ";\n")
    sz = sum(os.path.getsize(os.path.join(OUTD, f)) for f in os.listdir(OUTD))
    print(f"viewer data: {sorted(man['entries'])}, {sz/1e6:.1f} MB in {OUTD}")

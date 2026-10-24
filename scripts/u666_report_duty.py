"""Per-duty figures from the chain's postProcessing (WSL, vtk + matplotlib + PIL, single thread).
 usage: u666_report_render.py duty <case_dir> <out_dir> [max_gif_mb]
Conventions (override names in SURF/REGKEY below once the handoff gives the exact ones):
 * region stats: any postProcessing/**/*.dat with min/max/average(T) columns; region from the path.
 * planes: postProcessing/**/<time>/*.vtk|vtp|vtu whose path matches a SURF keyword; all files of one
   plane+time are merged (multi-region surfaces). T in K or C (auto).
"""
import sys, os, re, glob, json, io
import numpy as np
import vtk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image

SURF = {"axial": r"axial|y0|ymid|midplane_y", "mid": r"mid.?stack|radial.?mid|zmid|stack", "front": r"front", "rear": r"rear"}
REGKEY = {"end winding": r"endw|end.?wind", "winding": r"winding|slot|coil|copper", "magnets": r"magnet", "rotor": r"rotor",
          "housing": r"housing|frame"}
LIM = {"winding": 155, "end winding": 155, "magnets": 100}
COLOR = {"winding": "#d9822b", "end winding": "#a35a14", "magnets": "#b5323c", "rotor": "#2f9e8f", "housing": "#5b6675"}
READ = {".vtk": vtk.vtkGenericDataObjectReader, ".vtp": vtk.vtkXMLPolyDataReader, ".vtu": vtk.vtkXMLUnstructuredGridReader}


def C(a):
    a = np.asarray(a, float)
    return a - 273.15 if a.size and np.nanmean(a) > 200 else a


def region_of(path):
    p = path.lower()
    for k in REGKEY:                     # 'end winding' first so it wins over 'winding'
        if re.search(REGKEY[k], p):
            return k


def stats(pp):
    out = {}
    for f in sorted(glob.glob(os.path.join(pp, "**", "*.dat"), recursive=True)):
        reg = region_of(os.path.relpath(f, pp))
        hdr = [l for l in open(f) if l.startswith("#")]
        if not reg or not hdr:
            continue
        h = hdr[-1].lstrip("# ").strip()
        cols = re.split(r"\t|\s{2,}", h) if ("\t" in h or "  " in h) else h.split()
        rows = [l.split() for l in open(f) if l.strip() and not l.startswith("#")]
        if not rows:
            continue
        try:
            A = np.array([[float(x.strip("()")) for x in r] for r in rows])
        except ValueError:
            continue
        cols = cols[-A.shape[1]:] if len(cols) > A.shape[1] else cols

        def col(pat):
            for i, c in enumerate(cols):
                if re.search(pat, c, re.I) and "T" in c:
                    return A[:, i]
        t, mn, mx, av = A[:, 0], col(r"min"), col(r"max"), col(r"avg|average|mean")
        d = out.setdefault(reg, {"t": [], "min": [], "mean": [], "max": []})
        for k, v in zip(("min", "mean", "max"), (mn, av, mx)):
            d[k] += list(C(v)) if v is not None else [float("nan")] * len(t)
        d["t"] += list(t)
    for d in out.values():
        o = np.argsort(d["t"], kind="stable"); t = np.array(d["t"])[o]
        keep = np.r_[np.diff(t) > 0, True] if len(t) else []
        for k in d:
            d[k] = [float(x) for x in np.array(d[k])[o][keep]]
    return out


def tlimit(t, y, lim):
    t, y = np.array(t), np.array(y)
    i = np.where(y >= lim)[0]
    if not len(i):
        return None
    i = i[0]
    return float(t[i]) if i == 0 else float(t[i - 1] + (lim - y[i - 1]) / (y[i] - y[i - 1]) * (t[i] - t[i - 1]))


def curves(st, png):
    fig, ax = plt.subplots(figsize=(9, 5), dpi=100)
    for r, d in st.items():
        t = np.array(d["t"]) / 60
        ax.plot(t, d["max"], color=COLOR[r], lw=1.8, label=f"{r} max")
        ax.plot(t, d["mean"], color=COLOR[r], lw=1.2, ls="--", label=f"{r} mean")
    ax.axhline(155, color="#c0392b", lw=1, ls=":"); ax.text(0.01, 156, "winding limit 155 C", transform=ax.get_yaxis_transform(), fontsize=8, color="#c0392b")
    ax.axhline(100, color="#7d3c98", lw=1, ls=":"); ax.text(0.01, 101, "magnet limit 100 C", transform=ax.get_yaxis_transform(), fontsize=8, color="#7d3c98")
    ax.set_xlabel("time [min]"); ax.set_ylabel("T [C]"); ax.grid(alpha=.3); ax.legend(ncol=2, fontsize=7)
    fig.tight_layout(); fig.savefig(png); plt.close(fig)


def read_plane(files):
    P, V = [], []
    for f in files:
        rd = READ[os.path.splitext(f)[1]](); rd.SetFileName(f); rd.Update()
        o = rd.GetOutput()
        if o.GetNumberOfPoints() == 0:
            continue
        g = vtk.vtkGeometryFilter(); g.SetInputData(o); g.Update()
        tf = vtk.vtkTriangleFilter(); tf.SetInputData(g.GetOutput()); tf.Update(); o = tf.GetOutput()
        pts = np.array([o.GetPoint(i) for i in range(o.GetNumberOfPoints())])
        ids = o.GetPolys().GetData()
        a = np.array([ids.GetValue(i) for i in range(ids.GetNumberOfValues())]).reshape(-1, 4)[:, 1:]
        cd, pd = o.GetCellData().GetArray("T"), o.GetPointData().GetArray("T")
        if cd is not None:
            v = np.array([cd.GetValue(i) for i in range(len(a))])
        elif pd is not None:
            pv = np.array([pd.GetValue(i) for i in range(len(pts))]); v = pv[a].mean(1)
        else:
            continue
        P.append(pts[a]); V.append(v)
    if not P:
        return None
    P, V = np.concatenate(P), C(np.concatenate(V))
    ext = P.reshape(-1, 3).max(0) - P.reshape(-1, 3).min(0)
    drop = int(np.argmin(ext))
    keep = [2, 0] if drop == 1 else [i for i in range(3) if i != drop]   # axial plane: z horizontal, x vertical
    return P[:, :, keep] * 1000, V, ("z", "x") if drop == 1 else ("x", "y")


def planes(pp):
    """{plane: {time: [files]}}"""
    res = {}
    for f in glob.glob(os.path.join(pp, "**", "*"), recursive=True):
        if os.path.splitext(f)[1] not in READ or not os.path.isfile(f):
            continue
        rel = os.path.relpath(f, pp).lower().replace("\\", "/")
        m = re.search(r"(?:^|/)([0-9]+(?:\.[0-9]+)?(?:e[-+]?\d+)?)/", rel)
        if not m:
            continue
        for k, pat in SURF.items():
            if re.search(pat, rel):
                res.setdefault(k, {}).setdefault(float(m.group(1)), []).append(f)
                break
    return res


def draw(ax, data, lo, hi, title):
    P, V, ax_n = data
    pc = PolyCollection(P, array=V, cmap="inferno", edgecolors="none", clim=(lo, hi)); ax.add_collection(pc)
    ax.set_xlim(P[:, :, 0].min(), P[:, :, 0].max()); ax.set_ylim(P[:, :, 1].min(), P[:, :, 1].max())
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.set_xlabel(ax_n[0] + " [mm]"); ax.set_ylabel(ax_n[1] + " [mm]")
    return pc


def gif(frames, lo, hi, out, mb, name):
    """frames: [(t, data)]; shrinks until under mb."""
    for scale, nf in ((1.0, 36), (0.8, 30), (0.65, 24), (0.5, 20)):
        sel = np.linspace(0, len(frames) - 1, min(nf, len(frames))).round().astype(int)
        ims = []
        for i in sel:
            t, d = frames[i]
            fig, ax = plt.subplots(figsize=(6.4 * scale + 1, 5 * scale), dpi=80)
            pc = draw(ax, d, lo, hi, f"{name}  t = {t/60:.1f} min")
            fig.colorbar(pc, ax=ax, label="T [C]"); fig.tight_layout()
            b = io.BytesIO(); fig.savefig(b, format="png"); plt.close(fig); b.seek(0)
            ims.append(Image.open(b).convert("RGB").quantize(96, method=Image.Quantize.MEDIANCUT))
        ims[0].save(out, save_all=True, append_images=ims[1:], duration=120, loop=0, optimize=True)
        if os.path.getsize(out) <= mb * 1e6:
            return
    print("WARN gif still large", out, os.path.getsize(out))


def run(a):
    case, out = a[0], a[1]
    mb = float(a[2]) if len(a) > 2 else 2.8
    pp = os.path.join(case, "postProcessing")
    os.makedirs(out, exist_ok=True)
    info = {"case": case, "have": {}}
    st = stats(pp)
    if st:
        json.dump(st, open(os.path.join(out, "stats.json"), "w")); curves(st, os.path.join(out, "curves.png"))
        pk = {}
        for r, d in st.items():
            i = int(np.nanargmax(d["max"]))
            pk[r] = {"max": d["max"][i], "t_max": d["t"][i], "mean_end": d["mean"][-1], "max_end": d["max"][-1], "t_end": d["t"][-1],
                     "limit": LIM.get(r), "t_limit": tlimit(d["t"], d["max"], LIM[r]) if r in LIM else None}
        json.dump(pk, open(os.path.join(out, "peaks.json"), "w")); info["have"]["stats"] = True
    pl = planes(pp)
    if pl:
        last = {k: max(v) for k, v in pl.items()}
        fin = {k: read_plane(v[last[k]]) for k, v in pl.items()}
        fin = {k: v for k, v in fin.items() if v}
        if fin:
            lo = min(v[1].min() for v in fin.values()); hi = max(v[1].max() for v in fin.values())
            n = len(fin)
            fig, axs = plt.subplots(1, n, figsize=(4.2 * n, 4.6), dpi=100, squeeze=False)
            for ax, (k, d) in zip(axs[0], fin.items()):
                pc = draw(ax, d, lo, hi, f"{k}, t = {last[k]/60:.1f} min")
            fig.colorbar(pc, ax=axs[0].tolist(), label="T [C]", shrink=.8); fig.savefig(os.path.join(out, "contours.png")); plt.close(fig)
            info["have"]["contours"] = list(fin)
        for k, name in (("axial", "axial plane y=0"), ("mid", "mid-stack plane")):
            if k in pl and len(pl[k]) >= 3:
                fr = [(t, read_plane(f)) for t, f in sorted(pl[k].items())]
                fr = [(t, d) for t, d in fr if d]
                if len(fr) >= 3:
                    lo = min(d[1].min() for _, d in fr); hi = max(d[1].max() for _, d in fr)
                    gif(fr, lo, hi, os.path.join(out, f"anim_{k}.gif"), mb, name); info["have"]["gif_" + k] = len(fr)
    json.dump(info, open(os.path.join(out, "info.json"), "w"))
    print("duty done", info)

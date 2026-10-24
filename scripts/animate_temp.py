"""Temperature-rise animation: radial + axial sections heating from the cold start, fixed colour scale, live trace.

    .venv/Scripts/python -I scripts/animate_temp.py <result_case> <out.mp4> "<title>" [seconds]

Reads results/<case>/slices_<t>/<region>_{z,x}.vtk for every saved t (and t = 0 as uniform 40 C) and the monitor
histories in results/<case>/postProcessing. Frames blend linearly between saved solutions (same cut geometry).
"""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import imageio.v2 as imageio

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
case, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
SECONDS = float(sys.argv[4]) if len(sys.argv) > 4 else 12
FPS, K, T0 = 20, 273.15, 40.0
R = os.path.join(ROOT, "results", case)


def read_vtk(path):
    tok = open(path).read().split()
    i = tok.index("POINTS"); n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3)
    i = tok.index("POLYGONS"); m = int(tok[i + 1]); j = i + 3; tris = []
    for _ in range(m):
        k = int(tok[j]); ids = [int(t) for t in tok[j + 1:j + 1 + k]]; j += 1 + k
        tris += [(ids[0], ids[q], ids[q + 1]) for q in range(1, k - 1)]
    i = tok.index("FIELD"); nf = int(tok[i + 2]); j = i + 3; T = None
    for _ in range(nf):
        name, nc, nn = tok[j], int(tok[j + 1]), int(tok[j + 2]); j += 4
        if name == "T":
            T = np.array(tok[j:j + nc * nn], float)
        j += nc * nn
    return pts, np.array(tris), T - K


times = sorted(int(os.path.basename(d).split("_")[1]) for d in glob.glob(os.path.join(R, "slices_*"))
               if os.path.basename(d).split("_")[1].isdigit() and glob.glob(os.path.join(d, "*.vtk")))  # skip empty (unfinished) folders
regions = sorted({os.path.basename(f).rsplit("_", 1)[0] for f in glob.glob(os.path.join(R, f"slices_{times[-1]}", "*_z.vtk"))})
geo, field = {}, {}
for ax in ("z", "x"):
    for r in regions:
        f0 = os.path.join(R, f"slices_{times[-1]}", f"{r}_{ax}.vtk")
        if not os.path.exists(f0):
            continue
        pts, tris, _ = read_vtk(f0)
        X, Y = (pts[:, 0], pts[:, 1]) if ax == "z" else (-pts[:, 2], pts[:, 1])
        geo[(ax, r)] = (X * 1000, Y * 1000, tris)
        series = [np.full(len(pts), T0)]
        for t in times:
            series.append(read_vtk(os.path.join(R, f"slices_{t}", f"{r}_{ax}.vtk"))[2])
        field[(ax, r)] = np.array(series)
tt = np.array([0] + times, float)


def hist(region, kind="T"):
    d = os.path.join(R, "postProcessing", region, f"{kind}_{region}")
    if region == "winding" and case.startswith("detailed/"):     # detailed runs monitor the coil inside the copper region
        d = os.path.join(R, "postProcessing", "copper", f"{kind}_coil")
    a = np.vstack([np.atleast_2d(np.loadtxt(os.path.join(d, t, "volFieldValue.dat"), comments="#"))
                   for t in sorted(os.listdir(d), key=float)])
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    return a[:, 0], a[:, 1] - K


wt, wT = hist("winding"); mt, mT = hist("magnets")
try:
    mat, maT = hist("magnets", "Tavg")
except (OSError, ValueError):
    mat = maT = None
# report rule: the timeline ends when the winding hot spot reaches T_STOP (or at the last saved field); later data is dropped
T_STOP = 180.0
i = int(np.argmax(wT >= T_STOP))
tend = tt[-1] if wT[i] < T_STOP else (wt[0] if i == 0 else wt[i - 1] + (T_STOP - wT[i - 1]) * (wt[i] - wt[i - 1]) / (wT[i] - wT[i - 1]))
tend = min(tend, tt[-1])
n = int(np.searchsorted(tt, tend)) + 1            # keep the first snapshot at/after tend for blending
tt = tt[:n]; field = {k: v[:n] for k, v in field.items()}
vmax = max(f.max() for f in field.values())
cut = lambda t, T: (t[t <= tend], T[t <= tend])
wt, wT = cut(wt, wT); mt, mT = cut(mt, mT)
if mat is not None:
    mat, maT = cut(mat, maT)
unit, scale = ("h", 3600.0) if tend > 3 * 3600 else ("min", 60.0) if tend > 900 else ("s", 1.0)

fig = plt.figure(figsize=(12, 6.6), dpi=85)
fig.text(0.02, 0.955, title, fontsize=14, fontweight="bold")
fig.text(0.02, 0.92, "temperature from a 40 °C cold start · fixed colour scale · frames blended between saved solutions",
         fontsize=10, color="#555")
axz = fig.add_axes([0.01, 0.30, 0.38, 0.58]); axx = fig.add_axes([0.40, 0.30, 0.45, 0.58])
for a, name in ((axz, "radial section (z = 5 mm)"), (axx, "axial section (x = 0): rear left, drive end right")):
    a.set_aspect("equal"); a.axis("off"); a.set_title(name, fontsize=10, color="#333")
cax = fig.add_axes([0.88, 0.33, 0.015, 0.52])
axh = fig.add_axes([0.07, 0.06, 0.78, 0.18])
axh.plot(wt / scale, wT, color="#1f4e8c", lw=1.8, label="winding hot spot"); axh.plot(mt / scale, mT, color="#2e7d32", lw=1.5, label="magnet max")
if mat is not None:
    axh.plot(mat / scale, maT, color="#2e7d32", lw=1.2, ls=":", label="magnet mean")
axh.axhline(155, color="#c62828", ls="--", lw=0.9); axh.axhline(100, color="#c62828", ls=":", lw=0.9)
axh.set_xlim(0, tend / scale); axh.set_xlabel(f"time [{unit}]"); axh.set_ylabel("°C"); axh.legend(frameon=False, fontsize=8, loc="upper left")
axh.grid(alpha=0.3)
marker = axh.axvline(0, color="#c2185b", lw=1.5)
clock = fig.text(0.86, 0.13, "", fontsize=16, fontweight="bold", color="#c2185b")
arts = {}
for (ax, r), (X, Y, tris) in geo.items():
    a = axz if ax == "z" else axx
    arts[(ax, r)] = a.tripcolor(X, Y, tris, field[(ax, r)][0], shading="gouraud", cmap="turbo", vmin=T0, vmax=vmax)
for a, k in ((axz, "z"), (axx, "x")):
    xs = np.concatenate([g[0] for (ax, _), g in geo.items() if ax == k]); ys = np.concatenate([g[1] for (ax, _), g in geo.items() if ax == k])
    a.set_xlim(xs.min() - 3, xs.max() + 3); a.set_ylim(ys.min() - 3, ys.max() + 3)
cb = fig.colorbar(next(iter(arts.values())), cax=cax); cb.set_label("temperature [°C]")

frames = []
nf = int(SECONDS * FPS)
for f in range(nf):
    t = tend * f / (nf - 1)
    i = min(np.searchsorted(tt, t, side="right") - 1, len(tt) - 2); w = (t - tt[i]) / (tt[i + 1] - tt[i])
    for key, art in arts.items():
        art.set_array((1 - w) * field[key][i] + w * field[key][i + 1])
    marker.set_xdata([t / scale, t / scale])
    clock.set_text(f"t = {t/scale:.1f} {unit}" if unit != "s" else f"t = {t:.0f} s")
    fig.canvas.draw(); frames.append(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
plt.close(fig)
h, w_ = frames[0].shape[:2]
frames = [fr[: h - h % 2, : w_ - w_ % 2] for fr in frames]
imageio.mimwrite(out, frames, fps=FPS, codec="libx264", quality=5, pixelformat="yuv420p", macro_block_size=1)
print("wrote", out, len(frames), "frames, snapshots", len(tt))

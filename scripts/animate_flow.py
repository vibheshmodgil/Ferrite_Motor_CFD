"""Flow animation on a CFD section plane: tracer particles advected through the (steady) velocity field.

    .venv/Scripts/python -I scripts/animate_flow.py <slice.vtk> <z|x> <out.mp4|-> "<title>" <slowdown> [vmax|auto]
                                                    [--solids <slices dir>] [--still <out.png>]

Options may appear anywhere (before or after vmax).

z-plane: horizontal x, vertical y.  x-plane: horizontal -z (rear left, drive end right, as the section pictures).
Only the in-plane velocity moves the particles; colour = full speed |U|. slowdown = real seconds per video second
(1 = real time; 0.02 = 50x slow motion). Particles are released uniformly and re-released when they leave the
fluid, stop, or age out, so the pictures stay evenly covered.
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import os
import imageio.v2 as imageio

OPTS = {"--solids", "--still"}           # options that take a value; anything else is positional
args, opt_v, it = [], {}, iter(sys.argv[1:])
for a in it:
    if a in OPTS:
        opt_v[a] = next(it, None)
    elif a.startswith("--"):
        sys.exit(f"unknown option {a}")
    else:
        args.append(a)
src, ax, out, title, slow = args[0], args[1], args[2], args[3], float(args[4])
VMAX = float(args[5]) if len(args) > 5 and args[5] != "auto" else None
SOLIDS = opt_v.get("--solids")      # folder with <region>_<ax>.vtk solid sections on the same plane -> parts drawn + labelled
STILL = opt_v.get("--still")        # write a still picture (streamlines) to this .png instead of an animation
FPS, SECONDS, N, TRAIL = 20, 10, 1400, 10
rng = np.random.default_rng(1)


def read_vtk(path):
    tok = open(path).read().split()
    i = tok.index("POINTS"); n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3)
    i = tok.index("POLYGONS"); m = int(tok[i + 1]); j = i + 3; tris = []
    for _ in range(m):
        k = int(tok[j]); ids = [int(t) for t in tok[j + 1:j + 1 + k]]; j += 1 + k
        tris += [(ids[0], ids[q], ids[q + 1]) for q in range(1, k - 1)]
    fields = {}
    i = tok.index("FIELD"); nf = int(tok[i + 2]); j = i + 3
    for _ in range(nf):
        name, nc, nn = tok[j], int(tok[j + 1]), int(tok[j + 2]); j += 4
        fields[name] = np.array(tok[j:j + nc * nn], float).reshape(nn, nc); j += nc * nn
    return pts, np.array(tris), fields


pts, tris, F = read_vtk(src)
U = F["U"]
if ax == "z":
    X, Y, u, v = pts[:, 0], pts[:, 1], U[:, 0], U[:, 1]
else:
    X, Y, u, v = -pts[:, 2], pts[:, 1], -U[:, 2], U[:, 1]
X, Y = X * 1000, Y * 1000                                   # mm
# grid the slice: linear interpolation of the CFD points; a grid node is solid (masked) when its nearest CFD point is
# farther away than twice that point's own spacing to its neighbours (the motor is a hole with no points in it)
from scipy.interpolate import griddata, RegularGridInterpolator
Xall, Yall = X.copy(), Y.copy()                               # triangle vertices, before merging duplicates
key = np.round(np.column_stack([X, Y]), 4)
_, first = np.unique(key, axis=0, return_index=True)
X, Y, u, v, U = X[first], Y[first], u[first], v[first], U[first]
x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
h = max(x1 - x0, y1 - y0) / 700.0
gx, gy = np.arange(x0, x1 + h, h), np.arange(y0, y1 + h, h)
GX, GY = np.meshgrid(gx, gy)
# fluid mask: paint every CFD triangle of the slice onto the grid (exact footprint of the air; the motor is a hole)
from PIL import Image, ImageDraw
TX, TY = Xall, Yall
img = Image.new("L", (len(gx), len(gy)), 0); dr = ImageDraw.Draw(img)
for a, b, c in tris:
    dr.polygon([((TX[a] - gx[0]) / h, (TY[a] - gy[0]) / h), ((TX[b] - gx[0]) / h, (TY[b] - gy[0]) / h),
                ((TX[c] - gx[0]) / h, (TY[c] - gy[0]) / h)], fill=1, outline=1)
solid = np.asarray(img) == 0
gu = griddata((X, Y), u, (GX, GY), method="linear"); gv = griddata((X, Y), v, (GX, GY), method="linear")
spd_g = np.hypot(griddata((X, Y), U[:, 0], (GX, GY), method="linear"),
                 np.hypot(griddata((X, Y), U[:, 1], (GX, GY), method="linear"), griddata((X, Y), U[:, 2], (GX, GY), method="linear")))
for a in (gu, gv, spd_g):
    a[solid | np.isnan(a)] = np.nan
fu = RegularGridInterpolator((gy, gx), gu, bounds_error=False, fill_value=np.nan)
fv = RegularGridInterpolator((gy, gx), gv, bounds_error=False, fill_value=np.nan)
vmax = VMAX or np.nanpercentile(spd_g, 99.5)


def vel(p):
    q = np.column_stack([p[:, 1], p[:, 0]])
    a, b = fu(q), fv(q)
    bad = np.isnan(a) | np.isnan(b)
    return np.nan_to_num(a) * 1000, np.nan_to_num(b) * 1000, bad      # mm/s


def inside(c):
    a = fu(np.column_stack([c[:, 1], c[:, 0]]))
    return ~np.isnan(a)


def seed(k):
    p = np.empty((0, 2))
    while len(p) < k:
        c = np.column_stack([rng.uniform(x0, x1, 3 * k), rng.uniform(y0, y1, 3 * k)])
        p = np.vstack([p, c[inside(c)]])
    return p[:k]


P = seed(N); age = rng.uniform(0, 4, N); life = rng.uniform(2.5, 5.0, N)
hist = np.repeat(P[None], TRAIL, axis=0)
dt = slow / FPS                                             # real seconds advanced per frame

fig = plt.figure(figsize=(8, 8 * (y1 - y0) / (x1 - x0) * 0.9 + 0.7), dpi=90)
axp = fig.add_axes([0.03, 0.03, 0.82, 0.88])
tp = axp.imshow(np.ma.masked_invalid(spd_g), origin="lower", extent=(gx[0], gx[-1], gy[0], gy[-1]), cmap="viridis",
                vmin=0, vmax=vmax, interpolation="bilinear")
axp.contour(gx, gy, solid.astype(float), levels=[0.5], colors="#444", linewidths=1.0)
PART = {"housing": ("#a7adb5", "Housing (Al)"), "stator": ("#6b7078", "Stator teeth"), "winding": ("#c98b3c", "Winding (Cu)"),
        "rotor": ("#50555c", "Rotor"), "magnets": ("#26282b", "Magnets"), "shaft": ("#868b92", "Shaft"), "bearings": ("#c3c7cc", "Bearing")}
if SOLIDS:
    import glob as _g
    from matplotlib.collections import PolyCollection
    for f in sorted(_g.glob(os.path.join(SOLIDS, f"*_{ax}.vtk"))):
        reg = os.path.basename(f).rsplit("_", 1)[0]
        if reg not in PART:
            continue
        sp, st, _ = read_vtk(f)
        SX, SY = (sp[:, 0], sp[:, 1]) if ax == "z" else (-sp[:, 2], sp[:, 1])
        SX, SY = SX * 1000, SY * 1000
        polys = np.stack([np.column_stack([SX[t], SY[t]]) for t in st.T], axis=1)
        axp.add_collection(PolyCollection(polys, facecolors=PART[reg][0], edgecolors=PART[reg][0], linewidths=0.3, zorder=4))
        ar = 0.5 * np.abs((SX[st[:, 1]] - SX[st[:, 0]]) * (SY[st[:, 2]] - SY[st[:, 0]]) - (SX[st[:, 2]] - SX[st[:, 0]]) * (SY[st[:, 1]] - SY[st[:, 0]]))
        cx, cy = SX[st].mean(axis=1), SY[st].mean(axis=1)
        # label at the area-weighted point of the region that lies closest to its own mean (inside the part, not in a hole)
        mx, my = np.average(cx, weights=ar), np.average(cy, weights=ar); k = np.argmin(np.hypot(cx - mx, cy - my) / np.sqrt(ar + 1e-9) ** 0.2)
        axp.text(cx[k], cy[k], PART[reg][1], fontsize=8, ha="center", va="center", zorder=6, color="black",
                 bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2))
axp.set_aspect("equal"); axp.set_xlim(x0, x1); axp.set_ylim(y0, y1); axp.axis("off")
cb = fig.colorbar(tp, cax=fig.add_axes([0.88, 0.15, 0.025, 0.6])); cb.set_label("air speed [m/s]")
fig.text(0.03, 0.955, title, fontsize=13, fontweight="bold")
speedtxt = "real time" if slow == 1 else f"{1/slow:.0f}× slow motion"
fig.text(0.03, 0.925, f"tracer particles carried by the CFD velocity field · {speedtxt}", fontsize=10, color="#555")
lc = LineCollection([], linewidths=1.1); axp.add_collection(lc)
dots = axp.scatter([], [], s=4, c="white", edgecolors="none")

if STILL:
    gu_m, gv_m = np.ma.masked_invalid(gu), np.ma.masked_invalid(gv)
    axp.streamplot(gx, gy, gu_m.filled(0), gv_m.filled(0), color="white", linewidth=0.7, density=2.2, arrowsize=0.8, zorder=3,
                   broken_streamlines=True)
    fig.texts[1].set_text("streamlines of the in-plane CFD velocity · colour = air speed · grey = solid parts")
    dots.remove(); lc.remove()
    fig.savefig(STILL, dpi=110); print("wrote", STILL); sys.exit(0)

frames = []
for f in range(FPS * SECONDS):
    ua, va, bad1 = vel(P)
    mid = P + 0.5 * dt * np.column_stack([ua, va])
    ub, vb, bad2 = vel(mid)
    P = P + dt * np.column_stack([ub, vb]); age += dt / slow   # age in video seconds
    gone = bad1 | bad2 | ~inside(P) | (age > life) | (np.hypot(ub, vb) < 1e-4 * vmax * 1000)
    if gone.any():
        P[gone] = seed(gone.sum()); age[gone] = 0; life[gone] = rng.uniform(2.5, 5.0, gone.sum())
        hist[:, gone] = P[gone][None]
    hist = np.roll(hist, -1, axis=0); hist[-1] = P
    segs = np.stack([hist[:-1], hist[1:]], axis=2).transpose(1, 0, 2, 3).reshape(-1, 2, 2)
    alpha = np.tile(np.linspace(0.05, 0.9, TRAIL - 1), N)
    lc.set_segments(segs); lc.set_color(np.column_stack([np.ones((len(alpha), 3)), alpha]))
    dots.set_offsets(P)
    fig.canvas.draw()
    frames.append(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
plt.close(fig)
h, w = frames[0].shape[:2]
frames = [fr[: h - h % 2, : w - w % 2] for fr in frames]    # even size for H.264
imageio.mimwrite(out, frames, fps=FPS, codec="libx264", quality=5, pixelformat="yuv420p", macro_block_size=1)
print("wrote", out, len(frames), "frames")


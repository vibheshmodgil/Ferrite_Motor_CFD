"""U666 duty figures: contours on the 4 cut planes (final time), temperature mp4, energy-budget mp4, observations.

Called from u666_site.py (single thread, BelowNormal). Reads the VTK cut planes + volFieldValue .dat straight from the
WSL share. Everything is cached by the last available time + this script's mtime, so reruns only render what changed.
Cache: results/u666/report/cache/<duty>_<plane>.npz (polygon geometry once, T per saved time, appended incrementally).
"""
import json, re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import imageio.v2 as imageio

K, T0C = 273.15, 40.0
HERE = Path(__file__).resolve()
CACHE = HERE.parent.parent / "results/u666/report/cache"
ANIM = HERE.parent.parent / "results/u666/report/anim"
PLANES = [("axial_y0", "axial plane y = 0 (z horizontal)"), ("radial_stack", "mid-stack radial plane z = 29.9 mm"),
          ("radial_ew_front", "front end-winding plane z = 75 mm"), ("radial_ew_rear", "rear end-winding plane z = -15.3 mm")]
LIMREG = {"winding": 155.0, "magnets": 100.0}
FPS, SECONDS = 20, 12


def stamp():
    return HERE.stat().st_mtime


# ------------------------------------------------------------------ readers
def read_vtk(p):
    tok = Path(p).read_text().split()
    i = tok.index("POINTS"); n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3)
    i = tok.index("POLYGONS"); size = int(tok[i + 2]); a = np.array(tok[i + 3:i + 3 + size], int)
    polys, j = [], 0
    while j < len(a):
        k = a[j]; ids = list(a[j + 1:j + 1 + k]); polys.append((ids + [ids[-1]] * (4 - k))[:4]); j += 1 + k
    i = tok.index("FIELD"); nf = int(tok[i + 2]); j = i + 3; T = None
    for _ in range(nf):
        name, nc, nn = tok[j], int(tok[j + 1]), int(tok[j + 2]); j += 4
        if name == "T":
            T = np.array(tok[j:j + nc * nn], float)
        j += nc * nn
    return pts, np.array(polys), T - K


def proj(plane, pts):
    return (np.c_[pts[:, 2], pts[:, 0]] if plane == "axial_y0" else pts[:, :2]) * 1000


def plane_times(case, plane):
    """(times, regions): regions the plane never cuts (no vtk at any time) are dropped; times = common to the rest."""
    per = {}
    for d in (case / "postProcessing").glob(f"*/S_{plane}_*"):
        t = {x.name for x in d.iterdir() if (x / f"{plane}.vtk").exists()}
        if t:
            per[d.parent.name] = t
    if not per:
        return [], []
    ts = set.intersection(*per.values())
    return sorted(ts, key=float), sorted(per)


def load_plane(case, duty, plane):
    """-> dict(times, regs, polys (N,4,2), reg (N,), T (nt,N)) or None. Incremental npz cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{duty}_{plane}.npz"
    ts, regs = plane_times(case, plane)
    if not ts:
        return None
    old = None
    if f.exists():
        z = np.load(f, allow_pickle=True)
        if list(z["regs"]) == regs:
            old = {k: z[k] for k in z.files}
    have = [] if old is None else [str(x) for x in old["times"]]
    new = [t for t in ts if t not in have]
    if old is not None and not new:
        return old
    # a time must have all regions complete: skip the newest one if still being written (any region file missing)
    cols, T, done = [], [], []
    geo = None if old is None else (old["polys"], old["reg"])
    for t in new:
        Ts, P, RG = [], [], []
        try:
            rd = [read_vtk(case / "postProcessing" / r / f"S_{plane}_{r}" / t / f"{plane}.vtk") for r in regs]
        except Exception:      # newest time still being written: stop here, next run picks it up
            break
        for ri, (r, (pts, polys, Tc)) in enumerate(zip(regs, rd)):
            Ts.append(Tc)
            if geo is None:
                xy = proj(plane, pts)
                P.append(xy[polys]); RG.append(np.full(len(polys), ri))
        if geo is None:
            geo = (np.concatenate(P), np.concatenate(RG))
        Ts = np.concatenate(Ts)
        if len(Ts) != len(geo[0]):
            raise RuntimeError(f"{plane} t={t}: polygon count changed")
        T.append(Ts); done.append(t)
    if not done:
        return old
    out = dict(times=np.array(have + done), regs=np.array(regs), polys=geo[0], reg=geo[1],
               T=np.vstack(([old["T"]] if old is not None else []) + [np.array(T)]))
    np.savez_compressed(f, **out)
    return out


def series(case, reg, fo, fname="volFieldValue.dat"):
    """-> (array(t, value), volume) merged over all time dirs."""
    rows, vol = [], None
    d = case / "postProcessing" / reg / fo
    if not d.exists():
        return None, None
    for tdir in sorted(d.iterdir(), key=lambda x: float(x.name)):
        p = tdir / fname
        if not p.exists():
            continue
        for ln in p.read_text(errors="ignore").splitlines():
            if ln.startswith("# Volume"):
                vol = float(ln.split(":")[1])
            elif ln.strip() and not ln.startswith("#"):
                try:
                    rows.append([float(x) for x in ln.split()[:2]] if fname.startswith("vol") else [float(ln.split()[0]), float(ln.split()[4])])
                except (ValueError, IndexError):
                    pass
    if not rows:
        return None, vol
    a = np.array(rows)
    a = a[np.argsort(a[:, 0], kind="stable")]
    return a[np.r_[np.diff(a[:, 0]) > 0, True]], vol


# ------------------------------------------------------------------ contours (final time)
def _poly(ax, P, T, vmin, vmax, **kw):
    pc = PolyCollection(P, array=T, cmap="turbo", clim=(vmin, vmax), edgecolors="face", linewidths=0.15, **kw)
    ax.add_collection(pc)
    return pc


def _fit(ax, P):
    ax.set_xlim(P[..., 0].min() - 2, P[..., 0].max() + 2); ax.set_ylim(P[..., 1].min() - 2, P[..., 1].max() + 2)
    ax.set_aspect("equal"); ax.axis("off")


def contour_fig(case, duty, planes, out):
    """2x2 panels, shared colour bar, cells above their region limit hatched. Returns the final time."""
    D = {p: load_plane(case, duty, p) for p, _ in PLANES}
    D = {p: d for p, d in D.items() if d is not None}
    if not D:
        return None
    tf = max(float(d["times"][-1]) for d in D.values())
    key = "|".join(f"{p}{d['times'][-1]}" for p, d in sorted(D.items())) + f"|{stamp()}"
    if not _fresh(out, key):
        return tf
    vmax = max(float(d["T"][-1].max()) for d in D.values())
    vmax = max(vmax, 60.0)
    fig = plt.figure(figsize=(12, 8.6), dpi=90)
    fig.suptitle(f"{duty}: temperature at t = {tf:.0f} s, all regions", fontsize=13, fontweight="bold", x=0.02, ha="left")
    pcs = None
    for k, (p, title) in enumerate(PLANES):
        ax = fig.add_axes([0.02 + 0.45 * (k % 2), 0.50 - 0.45 * (k // 2) + 0.0, 0.43, 0.40])
        ax.set_title(title + (f", t = {float(D[p]['times'][-1]):.0f} s" if p in D else ""), fontsize=10)
        if p not in D:
            ax.text(0.5, 0.5, "no data", ha="center"); ax.axis("off"); continue
        d = D[p]; i = len(d["times"]) - 1
        pcs = _poly(ax, d["polys"], d["T"][i], T0C, vmax)
        for r, lim in LIMREG.items():
            if r in list(d["regs"]):
                m = (d["reg"] == list(d["regs"]).index(r)) & (d["T"][i] >= lim)
                if m.any():
                    ax.add_collection(PolyCollection(d["polys"][m], facecolors="none", edgecolors="k", hatch="////", linewidths=0.0))
        _fit(ax, d["polys"])
    cax = fig.add_axes([0.93, 0.12, 0.016, 0.76])
    cb = fig.colorbar(pcs, cax=cax); cb.set_label("temperature [°C]")
    for lim, c, name in ((155, "k", "155 winding"), (100, "k", "100 magnets")):
        if lim < vmax:
            cax.axhline(lim, color=c, lw=1.6); cax.text(-0.15, lim, name, ha="right", va="center", fontsize=8, transform=cax.get_yaxis_transform())
    fig.text(0.02, 0.03, "hatched cells: above the region limit (winding 155 °C, magnets 100 °C); colour scale shared by all four planes; "
             "regions drawn from their own cell values (no interpolation across interfaces).", fontsize=8.5, color="#555")
    fig.savefig(out); plt.close(fig); _mark(out, key)
    return tf


# ------------------------------------------------------------------ animations
def _fresh(out, key):
    k = Path(str(out) + ".key")
    if out.exists() and k.exists() and k.read_text() == key:
        return False
    return True


def _mark(out, key):
    Path(str(out) + ".key").write_text(key)


def grid(D):
    """(times float, T) with a uniform-T0 row at t = 0 if the plane has no t=0 output."""
    tt, T = D["times"].astype(float), D["T"]
    if tt[0] > 0:
        tt, T = np.r_[0.0, tt], np.vstack([np.full((1, T.shape[1]), T0C), T])
    return tt, T


def _blend(tt, A, t):
    i = int(min(np.searchsorted(tt, t, side="right") - 1, len(tt) - 2))
    w = (t - tt[i]) / (tt[i + 1] - tt[i])
    return (1 - w) * A[i] + w * A[i + 1]


def _writer(out):
    return imageio.get_writer(out, fps=FPS, codec="libx264", quality=5, pixelformat="yuv420p", macro_block_size=1)


def _grab(fig):
    fr = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    return np.ascontiguousarray(fr[: fr.shape[0] // 2 * 2, : fr.shape[1] // 2 * 2])


def anim_temp(case, duty, out, lp_title):
    A, B = load_plane(case, duty, "axial_y0"), load_plane(case, duty, "radial_stack")
    if A is None or B is None:
        return False
    (ta, TA), (tb, TB) = grid(A), grid(B)
    tend = min(ta[-1], tb[-1])
    if len(ta) < 3 or tend <= 0:
        return False
    key = f"{ta[-1]}|{tb[-1]}|{stamp()}"
    if not _fresh(out, key):
        return True
    vmax = max(TA.max(), TB.max())
    w, _ = series(case, "winding", "T_winding"); m, _ = series(case, "magnets", "T_magnets")
    unit, sc = ("min", 60.0) if tend > 900 else ("s", 1.0)
    fig = plt.figure(figsize=(12, 6.6), dpi=85)
    fig.text(0.02, 0.955, lp_title, fontsize=14, fontweight="bold")
    fig.text(0.02, 0.92, "temperature from a 40 °C cold start, fixed colour scale, frames blended between saved solutions (10 s)", fontsize=10, color="#555")
    a1 = fig.add_axes([0.01, 0.30, 0.50, 0.58]); a2 = fig.add_axes([0.52, 0.30, 0.33, 0.58])
    a1.set_title("axial plane y = 0 (z horizontal)", fontsize=10); a2.set_title("mid-stack radial plane", fontsize=10)
    p1 = _poly(a1, A["polys"], TA[0], T0C, vmax); p2 = _poly(a2, B["polys"], TB[0], T0C, vmax)
    _fit(a1, A["polys"]); _fit(a2, B["polys"])
    cb = fig.colorbar(p1, cax=fig.add_axes([0.89, 0.33, 0.015, 0.52])); cb.set_label("temperature [°C]")
    ax = fig.add_axes([0.07, 0.17, 0.78, 0.11])
    if w is not None:
        ax.plot(w[:, 0] / sc, w[:, 1] - K, color="#1f4e8c", lw=1.8, label="winding hot spot")
    if m is not None:
        ax.plot(m[:, 0] / sc, m[:, 1] - K, color="#2e7d32", lw=1.5, label="magnet max")
    ax.axhline(155, color="#c62828", ls="--", lw=.9); ax.axhline(100, color="#c62828", ls=":", lw=.9)
    ax.set_xlim(0, tend / sc); ax.set_xlabel(f"time [{unit}]"); ax.set_ylabel("°C"); ax.grid(alpha=.3); ax.legend(frameon=False, fontsize=8, loc="upper left")
    mk = ax.axvline(0, color="#c2185b", lw=1.5)
    clock = fig.text(0.87, 0.13, "", fontsize=15, fontweight="bold", color="#c2185b")
    nf = int(SECONDS * FPS)
    wr = _writer(out)
    for f in range(nf):
        t = tend * f / (nf - 1)
        p1.set_array(_blend(ta, TA, t)); p2.set_array(_blend(tb, TB, t))
        mk.set_xdata([t / sc, t / sc]); clock.set_text(f"t = {t/sc:.1f} {unit}")
        fig.canvas.draw(); wr.append_data(_grab(fig))
    wr.close(); plt.close(fig); _mark(out, key)
    return True


ORDER = ["winding", "stator", "wedge", "rotor", "magnets", "shaft", "bearings", "endcaps", "housing", "inair"]


def budget_data(case, duty, props):
    """Per-region stored energy [kJ] over time, injected + ambient-out cumulative energy. props = case_props.json dict."""
    rc, Q, tc, Tref, T0 = props["rhocv"], props["Q"], props["tc"], props["T_ref"], props["T0"]
    st = {}
    for reg in ORDER:
        r = rc.get(reg)
        parts = [(f"Tintz_{z}", v) for z, v in r.items()] if isinstance(r, dict) else [(f"Tint_{reg}", r)]
        tot, tgrid = None, None
        for fo, rho in parts:
            if fo == "Tintz_rpocket":
                continue    # air pocket, negligible
            a, vol = series(case, reg, fo)
            if a is None:
                tot = None; break
            e = rho * (a[:, 1] - T0 * vol) / 1000
            n = len(e) if tot is None else min(len(e), len(tot))
            tot = e[:n] if tot is None else tot[:n] + e[:n]
            tgrid = a[:n, 0]
        if tot is not None and tgrid is not None:
            st[reg] = (tgrid, tot)
    if "winding" not in st:
        return None
    t = st["winding"][0]
    n = min(len(v[0]) for v in st.values()); t = t[:n]
    S = np.array([st[r][1][:n] for r in st])
    names = list(st)
    wa, _ = series(case, "winding", "Tavg_winding")
    Tw = np.interp(t, wa[:, 0], wa[:, 1]) if wa is not None else np.full(n, Tref)
    P_in = Q["winding_dc"] * (1 + tc * (Tw - Tref)) + sum(v for k, v in Q.items() if k != "winding_dc")
    inj = np.r_[0, np.cumsum(0.5 * (P_in[1:] + P_in[:-1]) * np.diff(t))] / 1000
    out = np.zeros(n)
    for fo in ("Qout_housing", "Qout_shaft"):
        for reg in (fo.split("_")[1],):
            a, _ = series(case, reg, fo, "wallHeatFlux.dat")
            if a is not None:
                q = -np.interp(t, a[:, 0], a[:, 1]); out += np.r_[0, np.cumsum(0.5 * (q[1:] + q[:-1]) * np.diff(t))] / 1000
    return dict(t=t, names=names, S=S, inj=inj, out=out, P_in=P_in)


def anim_budget(case, duty, out, title, props):
    bd = budget_data(case, duty, props) if props else None
    if bd is None or len(bd["t"]) < 4:
        return False, None
    t, S = bd["t"], bd["S"]; key = f"{t[-1]}|{stamp()}"
    resid = (bd["inj"][-1] - bd["out"][-1] - S[:, -1].sum()) / max(bd["inj"][-1], 1e-9) * 100
    if not _fresh(out, key):
        return True, resid
    tend = t[-1]; sc, unit = (60.0, "min") if tend > 900 else (1.0, "s")
    S_tot = S.sum(0)
    # power view: dE/dt per region (kW->W) smoothed over 3 samples
    dS = np.gradient(S, t, axis=1) * 1000
    names = bd["names"]; y = np.arange(len(names))
    fig = plt.figure(figsize=(12, 6.6), dpi=80)
    fig.text(0.02, 0.955, title, fontsize=14, fontweight="bold")
    fig.text(0.02, 0.92, "left: energy stored in each region (kJ) · right: injected energy vs stored + leaving to ambient · bars on the right of the table: storing rate [W]", fontsize=9.5, color="#555")
    ax = fig.add_axes([0.10, 0.12, 0.34, 0.74])
    bars = ax.barh(y, S[:, 0], color="#ef8a3c"); ax.set_yticks(y, names); ax.invert_yaxis()
    ax.set_xlim(0, S[:, -1].max() * 1.35); ax.set_xlabel("stored energy [kJ]"); ax.grid(axis="x", alpha=.3)
    txt = [ax.text(0, yy, "", va="center", fontsize=8.5) for yy in y]
    bx = fig.add_axes([0.54, 0.12, 0.42, 0.74])
    cols = plt.cm.tab20(np.linspace(0, 1, len(names)))
    bx.stackplot(t / sc, S, colors=cols, labels=names, alpha=.85)
    bx.plot(t / sc, bd["inj"], "k", lw=2, label="injected")
    bx.plot(t / sc, S_tot + bd["out"], "k--", lw=1.2, label="stored + out (check)")
    bx.plot(t / sc, S_tot, color="#333", lw=0.8)
    bx.set_xlim(0, tend / sc); bx.set_ylim(0, bd["inj"].max() * 1.08); bx.set_xlabel(f"time [{unit}]"); bx.set_ylabel("kJ"); bx.grid(alpha=.3)
    bx.legend(fontsize=7, ncol=2, loc="upper left", frameon=False)
    mk = bx.axvline(0, color="#c2185b", lw=1.5)
    clock = fig.text(0.98, 0.955, "", fontsize=12, fontweight="bold", color="#c2185b", ha="right")
    nf = int(SECONDS * FPS); wr = _writer(out)
    TT = np.arange(len(t))
    for f in range(nf):
        tf = tend * f / (nf - 1)
        s = np.array([np.interp(tf, t, S[k]) for k in range(len(names))]); r = np.array([np.interp(tf, t, dS[k]) for k in range(len(names))])
        for b, v, tx, rr, yy in zip(bars, s, txt, r, y):
            b.set_width(v); tx.set_position((max(v, 0) + S[:, -1].max() * 0.02, yy)); tx.set_text(f"{v:.1f} kJ  {rr:+.0f} W")
        mk.set_xdata([tf / sc, tf / sc]); clock.set_text(f"t = {tf/sc:.1f} {unit}   injected {np.interp(tf, t, bd['inj']):.0f} kJ, stored {np.interp(tf, t, S_tot):.0f} kJ")
        fig.canvas.draw(); wr.append_data(_grab(fig))
    wr.close(); plt.close(fig); _mark(out, key)
    return True, resid


# ------------------------------------------------------------------ observations
def observations(case, duty, props, pk, resid, lim_notes=""):
    o = []
    if not pk:
        return o
    w, m = pk.get("winding"), pk.get("magnets")
    e, h = pk.get("endw"), pk.get("housing")
    if w:
        s = f"Winding hot spot reaches {w['max']:.1f} °C at {w['t']:.0f} s"
        s += f"; the 155 °C limit is crossed at {w['tl']:.0f} s ({w['tl']/60:.1f} min)." if w.get("tl") else "; the 155 °C limit is not reached."
        o.append(s)
    if m:
        o.append(f"Magnets peak at {m['max']:.1f} °C" + (f"; the 100 °C limit is crossed at {m['tl']:.0f} s." if m.get("tl") else ", below the 100 °C limit."))
    if e and w:
        o.append(f"End winding peaks {e['max']:.1f} °C vs slot {w['max']:.1f} °C ({e['max']-w['max']:+.1f} K): " + ("the end winding is the hot spot." if e['max'] > w['max'] else "the slot winding is the hot spot."))
    if h:
        o.append(f"Housing only reaches {h['max']:.1f} °C: heat is mostly stored in the motor at this duration (see budget animation)." if h['max'] < 80 else f"Housing reaches {h['max']:.1f} °C.")
    if resid is not None:
        o.append(f"Energy check: injected minus stored minus ambient outflow = {resid:+.1f} % of injected (copper-loss temperature feedback taken from the mean winding temperature).")
    return o[:5]

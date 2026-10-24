"""Time to the temperature limits per load point, from the OpenFOAM monitor histories.

    .venv/Scripts/python -I scripts/post.py [results_subdir]   # results/<lp>/postProcessing -> summary.json + plot
In the detailed model the winding hot spot is the real copper wire (region coil); in the baseline, region winding.
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = os.path.join(ROOT, "results", *sys.argv[1:2])
LP = json.load(open(os.path.join(ROOT, "loadpoints.json")))
LIMIT = {"winding": 155.0, "magnets": 100.0}        # C
K = 273.15


def hist(lp, region, kind="T"):
    if region == "winding" and os.path.isdir(os.path.join(RES, lp, "postProcessing", "coil")):
        region = "coil"
    d = os.path.join(RES, lp, "postProcessing", region, f"{kind}_{region}")
    # a continued run writes its history under <start time>/; stitch them in time order
    a = np.vstack([np.atleast_2d(np.loadtxt(os.path.join(d, t, "volFieldValue.dat"), comments="#"))
                   for t in sorted(os.listdir(d), key=float)])
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    return a[:, 0], a[:, 1] - K


def cross(t, T, lim):
    """First time T reaches lim (linear between samples), or None."""
    i = np.argmax(T >= lim)
    if T[i] < lim:
        return None
    return t[i] if i == 0 else t[i - 1] + (lim - T[i - 1]) * (t[i] - t[i - 1]) / (T[i] - T[i - 1])


summary = {}
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for lp, d in LP.items():
    if not os.path.isdir(os.path.join(RES, lp, "postProcessing", "magnets")):
        continue                                 # not run (or not finished) yet
    s = dict(torque=d["torque"], rpm=d["rpm"], P_shaft_kW=round(d["P_shaft_kW"], 2),
             loss_W={k: round(v, 1) for k, v in d["Q"].items()})
    for r, lim in LIMIT.items():
        t, T = hist(lp, r)
        tc = cross(t, T, lim)
        s[f"{r}_max_end_C"] = round(float(T[-1]), 1)
        s[f"{r}_rate_end_K_per_min"] = round(float((T[-1] - T[np.searchsorted(t, t[-1] - 600)]) / 10), 3) \
            if t[-1] > 1200 else None
        s[f"time_to_{r}_limit_s"] = None if tc is None else round(float(tc), 1)
        (axes[0] if r == "winding" else axes[1]).plot(t / 60, T, label=f"{lp} ({d['torque']:.0f} N·m, {d['rpm']} rpm)")
    s["t_end_s"] = float(t[-1])
    lims = [v for k, v in s.items() if k.startswith("time_to_") and v is not None]
    s["run_time_s"] = min(lims) if lims else None          # None = never reaches a limit in the window
    s["limited_by"] = None if not lims else min((v, k[8:-8]) for k, v in s.items()
                                                  if k.startswith("time_to_") and v is not None)[1]
    summary[lp] = s
    print(f"{lp:12s} {d['torque']:5.1f} N.m {d['rpm']:6d} rpm: "
          + (f"{s['run_time_s']:.0f} s ({s['run_time_s']/60:.1f} min), limited by {s['limited_by']}"
             if s["run_time_s"] else f"continuous (no limit in {t[-1]/3600:.1f} h)")
          + f"; end winding {s['winding_max_end_C']} C, magnet {s['magnets_max_end_C']} C")
for ax, (r, lim) in zip(axes, LIMIT.items()):
    ax.axhline(lim, color="k", ls="--", lw=1)
    ax.set(xlabel="time [min]", ylabel=f"max {r} temperature [°C]", title=f"{r} hot spot (limit {lim:.0f} °C)")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(RES, "temperatures.png"), dpi=130)
json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=1)

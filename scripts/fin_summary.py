"""Fin study summary -> results/fins/summary.json + summary.md

    .venv/Scripts/python -I scripts/fin_summary.py

Per variant (results/fins/<name>/, fin_run.sh): duty4 times to magnets 100 C and winding 155 C, the max temperatures
of winding / magnets / housing at those times and at the end, energy balance; screening UA and added mass from
results/fins/screen.json and mesh/fins/<name>/info.json; CFD convective hA from results/fins/<name>/air_hA.txt.
"""
import glob, json, os
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
W = os.path.join(ROOT, "results", "fins")
LIM = {"winding": 155.0, "magnets": 100.0}
SCREEN = {"baseline_eps0.1": "baseline (CAD fins, 2.5 mm uniform)", "ring_h16_p11.5": "ring H16 p11.5",
          "axial_h16_n68": "axial H16 N68", "axial_h12_n70": "axial H12 N70"}


def hist(d, r):
    f = sorted(glob.glob(os.path.join(d, "postProcessing", r, f"T_{r}", "*", "volFieldValue.dat")))
    a = np.loadtxt(f[-1], comments="#"); return a[:, 0], a[:, 1] - 273.15


def cross(t, T, lim):
    i = int(np.argmax(T >= lim))
    if T[i] < lim:
        return None
    return round(float(t[i - 1] + (lim - T[i - 1]) / (T[i] - T[i - 1]) * (t[i] - t[i - 1])) if i else float(t[0]))


scr = {r["name"]: r for r in json.load(open(os.path.join(W, "screen.json")))["all"]}
res = {}
for v in SCREEN:
    d = os.path.join(W, v)
    if not os.path.exists(os.path.join(d, "done")):
        continue
    H = {r: hist(d, r) for r in ("winding", "magnets", "housing")}
    o = {"screen_UA_WK": scr.get(SCREEN[v], {}).get("UA_WK")}
    info = os.path.join(ROOT, "mesh", "fins", v, "info.json")
    o["d_mass_kg"] = round(json.load(open(info))["d_mass_kg"], 3) if os.path.exists(info) else 0.0
    f = os.path.join(ROOT, "mesh", "fins", v, "air_hA.txt")
    if os.path.exists(f):
        o["cfd_conv_hA_WK"] = float(open(f).read().split("hA")[1].split()[0])
    t = H["winding"][0]
    for key, r in (("magnets_100C", "magnets"), ("winding_155C", "winding")):
        tc = cross(*H[r], LIM[r]); o[f"t_{key}_s"] = tc
        if tc is not None:
            o[f"T_at_{key}_C"] = {q: round(float(np.interp(tc, *H[q])), 1) for q in H}
    o["t_end_s"] = float(t[-1]); o["T_end_C"] = {q: round(float(H[q][1][-1]), 1) for q in H}
    eb = os.path.join(d, "energy_balance.json")
    if os.path.exists(eb):
        o["energy_error_pct"] = round(json.load(open(eb))["error_pct"], 2)
    res[v] = o
b = res.get("baseline_eps0.1", {})
md = ["# Housing fins: duty4 (9339 rpm, 3.24 N.m), baseline thermal model, eps 0.1 (bare machined Al)\n",
      "| variant | added Al kg | screen UA W/K | CFD conv hA W/K | magnets 100 C [s] | winding 155 C [s] | "
      "T at magnets 100 C (wdg/mag/hsg) | T end (wdg/mag/hsg) | energy % |", "|---|---|---|---|---|---|---|---|---|"]
for v, o in res.items():
    def dt(k):
        x, x0 = o.get(k), b.get(k)
        return "-" if x is None else f"{x:.0f}" + (f" ({x - x0:+.0f})" if x0 and v != "baseline_eps0.1" else "")
    tm = o.get("T_at_magnets_100C_C", {}); te = o["T_end_C"]
    md.append(f"| {v} | {o['d_mass_kg']:+.2f} | {o['screen_UA_WK']} | {o.get('cfd_conv_hA_WK', '-')} | {dt('t_magnets_100C_s')} | "
              f"{dt('t_winding_155C_s')} | {'/'.join(str(tm.get(q, '-')) for q in ('winding', 'magnets', 'housing'))} | "
              f"{'/'.join(str(te[q]) for q in ('winding', 'magnets', 'housing'))} @ {o['t_end_s']:.0f} s | {o.get('energy_error_pct', '-')} |")
json.dump(res, open(os.path.join(W, "summary.json"), "w"), indent=1)
open(os.path.join(W, "summary.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))

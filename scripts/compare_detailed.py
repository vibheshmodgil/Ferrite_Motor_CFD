"""Detailed (real coils, bobbins, resin, busbars) vs baseline (smeared winding) thermal model, per duty point.

    python compare_detailed.py duty1 duty4      -> results/detailed_vs_baseline.json + .md

Reads results/<lp>/ (baseline) and results/detailed/<lp>/ (detailed): postProcessing T_<region> max histories and
the heatflow_<t>.txt of the last common written time.
"""
import glob, json, os, sys
import numpy as np

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
LIM = {"winding": 155.0, "magnets": 100.0}


def hist(d, region, kind="T"):
    f = (glob.glob(os.path.join(d, "postProcessing", region, f"{kind}_{region}", "*", "volFieldValue.dat")) or
         glob.glob(os.path.join(d, "postProcessing", "copper", f"{kind}_{region}", "*", "volFieldValue.dat")))  # merged Cu zones
    if not f:
        return None
    a = np.loadtxt(sorted(f)[-1], comments="#")
    return a[:, 0], a[:, 1] - 273.15


def t_cross(h, lim):
    t, T = h
    i = np.argmax(T >= lim)
    if T[i] < lim:
        return None
    return round(float(t[i - 1] + (lim - T[i - 1]) / (T[i] - T[i - 1]) * (t[i] - t[i - 1])) if i else float(t[0]))


def flows(d):
    fs = glob.glob(os.path.join(d, "heatflow_*.txt"))
    if not fs:
        return None, {}
    f = max(fs, key=lambda p: float(p.rsplit("_", 1)[1][:-4]))
    q = {}
    for l in open(f):
        r, p, v = l.split()
        q[f"{r}:{p}"] = float(v)
    return float(f.rsplit("_", 1)[1][:-4]), q


def summary(d, wind):
    out = {}
    for r in (wind, "magnets", "housing", "stator", "rotor", "busbar", "strap", "tbar", "bobbin", "resin"):
        h = hist(d, r)
        if h:
            out[r] = {"T_end_C": round(float(h[1][-1]), 1), "T_max_C": round(float(h[1].max()), 1)}
    h = hist(d, wind, "Tavg")
    if h:
        out[wind]["T_avg_end_C"] = round(float(h[1][-1]), 1)
    out["t_end_s"] = float(hist(d, wind)[0][-1])
    out["t_winding_155C_s"] = t_cross(hist(d, wind), LIM["winding"])
    out["t_magnet_100C_s"] = t_cross(hist(d, "magnets"), LIM["magnets"])
    out["heatflow_time_s"], q = flows(d)
    out["heat_W"] = {k: round(v, 1) for k, v in q.items()}
    return out


NOTES = """## Why they differ
- Hot spot vs mean: the baseline winding is a smeared block with isotropic k = 1 W/mK, so heat cannot run along the
  wire and the slot centre peaks (duty1 max - mean ~40 K). The real wire (k 390) spreads heat along every turn
  (max - mean ~12 K): lower hot spot and a later 155 C crossing, but a HIGHER winding mean.
- Higher mean: all copper heat must cross the resin (0.25 W/mK) and the PA66 bobbin (0.35 W/mK) to reach the teeth.
  The baseline lumps this into one 1.7 mm / 0.30 W/mK layer and lets the end-winding block dump heat straight into
  the end-space air (duty1: 277 W baseline winding -> inair, vs 53 W copper -> inair + 126 W resin -> inair).
- Magnets / housing: within ~3-5 C; the stator-to-housing path and the outer h are the same. The magnets cross
  100 C slightly later in duty4 (851 vs 800 s) because less end-winding heat reaches the end-space air and rotor.
- Busbars / strap / terminal bars run 10-35 C below the coil hot spot: heated mainly by conduction from the coil
  leads; their own Joule heat is small (duty1 ~29 W at 20 C, of which busbar_20C 18.7 W).

## Model approximations (detailed mesh)
- CAD is the v7 motor_65 assembly: 65 mm stack vs 64 mm in Design9795_1, 30 mm shaft vs 25 mm; stator OD, bore and
  rotor diameter match.
- Coil = bare 2.9 mm Cu re-swept from the CAD centreline; the 0.05 mm enamel is meshed as resin (0.25 ~ 0.22 W/mK).
- Bobbin simplified (the CAD bobbins float 0.10-0.25 mm off the tooth with overlapping micro-faces and would not
  mesh): box sleeve + stepped end walls sharing the tooth faces, 4457 vs 4773 mm3 per bobbin, >= 0.27 mm from wire.
- coil, strap, busbar and tbar merged into one region "copper" (same metal, physically continuous); each part is a
  cellZone with its own Joule source. As separate regions the segregated Cu-Cu coupling stalled (energy -1.3 %).
- 4 tiny (4 mm3) air pockets in the rear-cover screw holes got no cells (adiabatic voids). 2 cells with aspect
  ratio 1225 fail checkMesh (acceptable for solid conduction); max non-orthogonality 88.8, skewness 3.14.
- Outer h re-mapped from the external-air CFD onto the detailed housing faces (results/h_cfd_detailed.json).
- Adiabatic energy test, 300 s: -0.9 % (results/energy_test_detailed.json). duty4 global balance is -1.7 to -2.1 %
  (baseline -1.16 %): the 60 s steps hit the 100-corrector cap early in the run, so treat duty4 temperatures as
  ~1-2 % of stored heat low.
- duty1: both runs end at 477 s (the baseline died there); fields saved at 420 s.
"""

res, md = {}, ["# Detailed vs baseline thermal model\n"]
for lp in sys.argv[1:]:
    b, dd = summary(os.path.join(W, lp), "winding"), summary(os.path.join(W, "detailed", lp), "coil")
    res[lp] = {"baseline": b, "detailed": dd}
    md += [f"## {lp}\n", "| quantity | baseline | detailed |", "|---|---|---|",
           f"| end time [s] | {b['t_end_s']:.0f} | {dd['t_end_s']:.0f} |",
           f"| winding / coil max at end [C] | {b['winding']['T_end_C']} | {dd['coil']['T_end_C']} |",
           f"| winding / coil mean at end [C] | {b['winding'].get('T_avg_end_C')} | {dd['coil'].get('T_avg_end_C')} |",
           f"| magnet max at end [C] | {b['magnets']['T_end_C']} | {dd['magnets']['T_end_C']} |",
           f"| housing max at end [C] | {b['housing']['T_end_C']} | {dd['housing']['T_end_C']} |",
           f"| stator max at end [C] | {b['stator']['T_end_C']} | {dd['stator']['T_end_C']} |",
           f"| time to 155 C winding [s] | {b['t_winding_155C_s']} | {dd['t_winding_155C_s']} |",
           f"| time to 100 C magnet [s] | {b['t_magnet_100C_s']} | {dd['t_magnet_100C_s']} |"]
    md += [f"| {r} max at end [C] | - | {dd[r]['T_end_C']} |" for r in ("busbar", "strap", "tbar", "bobbin", "resin") if r in dd]
    md += ["", f"Heat crossing interfaces (W, + = into the first region), baseline at t = {b['heatflow_time_s']}, "
           f"detailed at t = {dd['heatflow_time_s']}:", ""]
    for name, s in (("baseline", b), ("detailed", dd)):
        md.append(f"- {name}: " + ", ".join(f"{k} {v:+.1f}" for k, v in sorted(s["heat_W"].items(), key=lambda kv: -abs(kv[1]))[:12]))
    md.append("")
    eb = os.path.join(W, "detailed", lp, "energy_balance.json")   # scripts/energy_balance_detailed.py
    if os.path.exists(eb):
        e = json.load(open(eb)); res[lp]["detailed"]["energy_balance"] = e
        md += [f"Global energy balance, detailed run (generation vs outflow + storage): "
               f"{e['error_pct_range'][0]:+.1f} to {e['error_pct_range'][1]:+.1f} %", ""]
md.append(NOTES)
json.dump(res, open(os.path.join(W, "detailed_vs_baseline.json"), "w"), indent=1)
open(os.path.join(W, "detailed_vs_baseline.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))

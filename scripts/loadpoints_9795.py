"""Duty points (slide 3) -> heat sources for Design9795_1 (copper), from the Lab maps at 100 C (Design9795_1/lab_100C.json,
FEMM d-q map + Motor-CAD loss settings, model v3 with 3 skew slices). Updates duty1..duty5 in loadpoints.json, other entries kept.

    python scripts/loadpoints_9795.py

Q.winding_100C = DC copper at 100 C (the case scales it with temperature); Q.winding_ac = AC copper extra (constant W);
stator / rotor iron from the maps; mechanical from motorcad_losses.json: bearings (front + rear) and windage, both x (n/2600)^1.3.
Magnet loss ~0 (ferrite, Motor-CAD 0 W).
"""
import json, math, os
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "..", "ferrite_repo", "repo", "Design9795_1")
LAB = json.load(open(os.path.join(D, "lab_100C.json")))
LOSS = json.load(open(os.path.join(D, "motorcad_losses.json")))

DUTY = [   # name, torque N.m, speed rpm, (end time, step, write interval [s])
    ("duty1", 37.0, 1782, (1800, 3, 60)),       # grade 12.3 % @ 23 km/h, highest loss, 5 min
    ("duty2", 26.3, 2550, (3600, 10, 300)),     # 15 min
    ("duty3", 20.0, 3637, (5400, 20, 300)),     # 30 min
    ("duty4", 3.24, 9339, (10800, 60, 900)),    # flat 60 km/h, top speed, 45 min
    ("duty5", 12.43, 1612, (10800, 60, 900)),   # 45 min
]

# same air constants and correlations as loadpoints.py (copied: importing it would rewrite loadpoints.json)
K_AIR, NU_AIR = 0.030, 2.1e-5
R_ROT, GAP = 0.053, 0.0005
L_END = 0.010


def gap_k(rpm):
    w = rpm * 2 * math.pi / 60
    ta = w * w * (R_ROT + GAP / 2) * GAP ** 3 / NU_AIR ** 2
    nu = 2.0 if ta < 1740 else 0.128 * ta ** 0.367 if ta < 1e4 else 0.409 * ta ** 0.241
    return K_AIR * nu / 2, ta


def endspace_k(rpm):
    h = 15 + 6.75 * (rpm * 2 * math.pi / 60 * R_ROT) ** 0.65
    return h * L_END, h


def interp(key, T, n):
    """Bilinear on the (torque, speed) map; all four corners must be inside the envelope."""
    a = np.array([[np.nan if v is None else v for v in r] for r in LAB["maps"][key]], float)
    ts, ns = LAB["torques"], LAB["speeds"]
    i, j = np.searchsorted(ts, T) - 1, np.searchsorted(ns, n) - 1
    u, v = (T - ts[i]) / (ts[i + 1] - ts[i]), (n - ns[j]) / (ns[j + 1] - ns[j])
    return float((1 - u) * (1 - v) * a[i, j] + u * (1 - v) * a[i + 1, j] + (1 - u) * v * a[i, j + 1] + u * v * a[i + 1, j + 1])


def mech(n):
    b, w = LOSS["bearing"], LOSS["windage"]
    return ((b["front_W"] + b["rear_W"]) * (n / b["ref_rpm"]) ** b["exponent"], w["W"] * (n / w["ref_rpm"]) ** w["exponent"])


fn = os.path.join(ROOT, "loadpoints.json")
out = json.load(open(fn)) if os.path.exists(fn) else {}
print("point   N.m   rpm    Cu_dc  Cu_ac  Fe_st  Fe_rot  bear  wind   total W   I_line A  V_ph/V_max")
for name, T, n, run in DUTY:
    v = {k: interp(k, T, n) for k in ("pcu", "pac", "pfe_st", "pfe_rot", "loss", "I_line", "V_ph")}
    assert not any(math.isnan(x) for x in v.values()), f"{name}: {T} N.m @ {n} rpm is outside the torque-speed envelope"
    pb, pw = mech(n)
    kg, ta = gap_k(n)
    ke, he = endspace_k(n)
    il = v["I_line"]
    out[name] = dict(
        torque=T, rpm=n, P_shaft_kW=T * n * 2 * math.pi / 60 / 1e3,
        Q=dict(winding_100C=v["pcu"], winding_ac=v["pac"], stator=v["pfe_st"], rotor=v["pfe_rot"], bearings=pb, inair=pw),
        k_gap=kg, taylor=ta, k_inair=ke, h_endspace=he,
        I_line=il, busbar_20C=28.25 * (il / 360.3) ** 2, J_strap=il / math.sqrt(3) / 2 / 9e-6, J_tbar=il / 30e-6,
        source="Design9795_1 lab_100C.json (copper, 52 V, 100 C)", **dict(zip(("end_time", "dt", "write"), run)))
    print(f"{name}  {T:5.2f} {n:5d}  {v['pcu']:6.1f} {v['pac']:6.1f} {v['pfe_st']:6.1f} {v['pfe_rot']:6.1f} {pb:6.1f} {pw:5.1f}"
          f"  {sum(out[name]['Q'].values()):7.1f}  {il:7.1f}   {v['V_ph']:.1f}/{LAB['info']['V_max']:.1f}")
json.dump(out, open(fn, "w"), indent=1)

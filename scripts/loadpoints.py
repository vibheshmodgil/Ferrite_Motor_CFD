"""Load points -> heat sources per region + internal-air conduction, from the FEMM loss map (femm_em/eff.json).

    python scripts/loadpoints.py      # -> loadpoints.json

Copper loss in eff.json is DC at 100 C; the case scales it with (1 + 0.00393 (T - 100)) per cell.
Iron loss includes the rotor share (ROTOR_FE); mechanical = MECH_A n (bearings) + MECH_B n^2 (windage).
"""
import json, math, os
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
E = json.load(open(os.path.join(ROOT, "..", "OUTPUT", "femm_em", "eff.json")))
M = E["model"]

LOADPOINTS = [   # name, torque N.m, speed rpm
    ("peak_torque", 45.0, 2000),
    ("peak_power", 16.0, 6000),
    ("continuous", 24.0, 3000),
    ("cruise", 8.0, 6000),
    ("max_speed", 8.0, 12000),
    # vehicle duty cycle (slide 3): S.No 1 grade 12.3 % @ 23 km/h = highest loss, S.No 4 flat 60 km/h = top speed
    ("grade12", 37.0, 1782),
    ("flat60", 3.24, 9339),
]
RUN = {"grade12": (900, 3, 60), "flat60": (10800, 60, 900)}   # end time, step, write interval [s]: >= 3x target duration

# air at ~80 C
K_AIR, NU_AIR = 0.030, 2.1e-5
R_ROT, GAP = 0.053, 0.0005
L_END = 0.010            # ponytail: end-space convection as conduction over 10 mm, k = h L; a CFD of the rotating
                         # end space would replace this


def interp(key, T, n):
    """Bilinear on the (torque, speed) map; corners with zero weight are skipped, so points on the envelope edge
    don't pick up the NaN beyond it."""
    a, ts, ns = np.array(E[key], dtype=float), E["torques"], E["speeds"]
    i = min(max(np.searchsorted(ts, T) - 1, 0), len(ts) - 2)
    j = min(max(np.searchsorted(ns, n) - 1, 0), len(ns) - 2)
    u, v = (T - ts[i]) / (ts[i + 1] - ts[i]), (n - ns[j]) / (ns[j + 1] - ns[j])
    w = {(0, 0): (1 - u) * (1 - v), (1, 0): u * (1 - v), (0, 1): (1 - u) * v, (1, 1): u * v}
    return sum(wk * a[i + di, j + dj] for (di, dj), wk in w.items() if wk > 1e-12)


def gap_k(rpm):
    """Air-gap effective conductivity, Taylor-Couette (Becker-Kaye as used in motor thermal networks)."""
    w = rpm * 2 * math.pi / 60
    ta = w * w * (R_ROT + GAP / 2) * GAP ** 3 / NU_AIR ** 2
    nu = 2.0 if ta < 1740 else 0.128 * ta ** 0.367 if ta < 1e4 else 0.409 * ta ** 0.241
    return K_AIR * nu / 2, ta          # Nu = 2 is pure conduction across the gap


def endspace_k(rpm):
    v = rpm * 2 * math.pi / 60 * R_ROT
    h = 15 + 6.75 * v ** 0.65          # end-winding / end-cap convection vs rotor tip speed (Schubert)
    return h * L_END, h


out = {}
for name, T, n in LOADPOINTS:
    pcu, pfe, pme, irms = (float(interp(k, T, n)) for k in ("pcu", "pfe", "pmech", "I_rms"))
    assert not math.isnan(pcu), f"{name}: {T} N.m @ {n} rpm is outside the torque-speed envelope"
    kg, ta = gap_k(n)
    ke, he = endspace_k(n)
    out[name] = dict(
        torque=T, rpm=n, P_shaft_kW=T * n * 2 * math.pi / 60 / 1e3,
        Q=dict(winding_100C=pcu, stator=pfe / (1 + M["ROTOR_FE"]), rotor=pfe * M["ROTOR_FE"] / (1 + M["ROTOR_FE"]),
               bearings=M["MECH_A"] * n, inair=M["MECH_B"] * n * n),
        k_gap=kg, taylor=ta, k_inair=ke, h_endspace=he,
        # detailed model: busbar plates 28.25 W at 360.3 A rms line, 20 C (busbar optimisation, "Balanced");
        # straps carry the path current (line / sqrt3 / 2 parallel) in 4.5 x 2 mm, terminal bars the line current in 3 x 10 mm
        I_line=irms, busbar_20C=28.25 * (irms / 360.3) ** 2,
        J_strap=irms / math.sqrt(3) / 2 / 9e-6, J_tbar=irms / 30e-6)
    if name in RUN:
        out[name].update(zip(("end_time", "dt", "write"), RUN[name]))
    q = out[name]["Q"]
    print(f"{name:12s} {T:5.1f} N.m {n:6d} rpm  Cu {pcu:6.1f}  Fe {pfe:6.1f}  mech {pme:5.1f} W   "
          f"gap k {kg:.3f} (Ta {ta:.0f})  end-space h {he:.0f} -> k {ke:.2f}  I {irms:.0f} A")
json.dump(out, open(os.path.join(ROOT, "loadpoints.json"), "w"), indent=1)

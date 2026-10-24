"""U666 36-slot winding: effective in-slot properties vs copper fill factor.

Geometry: 5 parallel strands per conductor, bare Cu d = 0.71 mm, enamelled D = 0.76 mm,
slot liner 0.25 mm (k 0.15), varnish fills gaps (k 0.25, no potting).

Fill factor Kf = bare Cu area / slot area (slot area taken inside the liner).
Conductor (Cu + enamel) area fraction  Kc = Kf * (D/d)^2 ; varnish fraction = 1 - Kc.

Transverse k:
  Stage 1, strand bundle: Hashin-Shtrikman lower bound (Hashin & Shtrikman 1962),
    3D conductivity form  k_HS- = k1 + f2 / [ 1/(k2-k1) + f1/(3 k1) ],
    k1 = lower-k phase (matrix), k2 = inclusion. Cu inclusions in enamel matrix, f = (d/D)^2.
  Stage 2, winding: same HS lower bound, conductor as inclusion in varnish matrix, f = Kc.
  Layered check: Wiener series bound (layers normal to heat flow),
    1/k = sum_i f_i / k_i over Cu, enamel, varnish. Must not exceed the HS value.
Axial k: rule of mixtures (Voigt, parallel layers): k = sum_i f_i k_i.
Density and cp: rho = sum f_i rho_i (volume-weighted); cp = sum f_i rho_i cp_i / rho (mass-weighted).
Liner: contact resistance per m^2, R = t / k_liner, for the winding/stator interface.

ASSUMED (not supplied in the brief): enamel and varnish rho and cp are typical polyimide /
epoxy values. Change the constants below if the datasheet differs.

Usage:
  python u666_winding_props.py            -> table for Kf = 0.30 ... 0.50
  python u666_winding_props.py 0.42 0.38  -> table for the given Kf values
"""
import json
import math
import os
import sys

K_CU, RHO_CU, CP_CU = 390.0, 8933.0, 385.0
K_EN, RHO_EN, CP_EN = 0.2, 1420.0, 1100.0    # enamel rho/cp ASSUMED
K_VA, RHO_VA, CP_VA = 0.25, 1200.0, 1300.0   # varnish rho/cp ASSUMED
K_LINER, T_LINER = 0.15, 0.25e-3             # m
D_BARE, D_OVER = 0.71e-3, 0.76e-3            # m
N_STRANDS = 5
DEFAULT_KF = [0.30, 0.35, 0.40, 0.45, 0.50]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "results", "u666")
OUT_JSON = os.path.join(OUT_DIR, "winding_props.json")


def area_turn():
    """Bare copper area per turn (one conductor = N_STRANDS strands), m^2."""
    return N_STRANDS * math.pi / 4 * D_BARE ** 2


def hs_lower(k1, k2, f2):
    """Hashin-Shtrikman lower bound, 2 phases, k1 = lower-k matrix phase, f2 = inclusion fraction."""
    f1 = 1.0 - f2
    return k1 + f2 / (1.0 / (k2 - k1) + f1 / (3.0 * k1))


def props(kf):
    fcond = (D_BARE / D_OVER) ** 2            # Cu share of the conductor (Cu + enamel)
    kc = min(1.0, kf / fcond)                 # conductor area fraction, clamped at 1
    f_cu, f_en, f_va = kf, kc - kf, 1.0 - kc

    cu_in_cond = kf / kc if kc > 0 else fcond
    k_cond = hs_lower(K_EN, K_CU, cu_in_cond) if kc > 0 else K_EN
    k_t_hs = hs_lower(K_VA, k_cond, kc)
    k_t_layer = 1.0 / (f_cu / K_CU + f_en / K_EN + f_va / K_VA)
    k_ax = f_cu * K_CU + f_en * K_EN + f_va * K_VA

    rho = f_cu * RHO_CU + f_en * RHO_EN + f_va * RHO_VA
    cp = (f_cu * RHO_CU * CP_CU + f_en * RHO_EN * CP_EN + f_va * RHO_VA * CP_VA) / rho

    return {
        "Kf": kf,
        "Kc_conductor_fraction": kc,
        "f_copper": f_cu,
        "f_enamel": f_en,
        "f_varnish": f_va,
        "k_strand_bundle_HS": k_cond,
        "k_transverse_HS_lower": k_t_hs,
        "k_transverse_layered_check": k_t_layer,
        "k_axial_ROM": k_ax,
        "rho_homog": rho,
        "cp_homog": cp,
        "R_liner_m2K_per_W": T_LINER / K_LINER,
    }


def self_check():
    z = props(1e-12)
    assert abs(z["k_transverse_HS_lower"] - K_VA) < 1e-6, "Kf->0 transverse must be varnish k"
    o = props(1.0)
    assert abs(o["k_axial_ROM"] - K_CU) < 1e-9, "Kf=1 axial must be copper k"
    for kf in DEFAULT_KF:
        r = props(kf)
        assert abs(r["f_copper"] + r["f_enamel"] + r["f_varnish"] - 1.0) < 1e-12
        assert K_VA <= r["k_transverse_HS_lower"] <= K_CU
        assert r["k_transverse_layered_check"] <= r["k_transverse_HS_lower"] + 1e-12
    assert abs(T_LINER / K_LINER - 1.6667e-3) < 1e-6
    assert abs(area_turn() * 1e6 - 1.9795) < 1e-3


def main(argv):
    self_check()
    kfs = [float(a) for a in argv] if argv else DEFAULT_KF
    rows = [props(kf) for kf in kfs]

    print(f"Area per turn (5 x pi/4 x 0.71^2) = {area_turn() * 1e6:.4f} mm^2")
    print("fill factor = N_cond_per_slot * A_turn / A_slot")
    print(f"{'Kf':>5} {'k_T HS':>8} {'k_T layer':>10} {'k_axial':>9} {'rho':>8} {'cp':>8} {'R_liner':>10}")
    for r in rows:
        print(f"{r['Kf']:5.2f} {r['k_transverse_HS_lower']:8.4f} {r['k_transverse_layered_check']:10.4f} "
              f"{r['k_axial_ROM']:9.2f} {r['rho_homog']:8.1f} {r['cp_homog']:8.1f} {r['R_liner_m2K_per_W']:10.3e}")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"area_per_turn_m2": area_turn(), "rows": rows}, fh, indent=2)
    print(f"saved {OUT_JSON}")


if __name__ == "__main__":
    main(sys.argv[1:])

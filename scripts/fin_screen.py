"""Housing fin screening, no CFD: UA (W/K) at T_wall 100 C / ambient 40 C, added Al mass and heat capacity.
    .venv/Scripts/python -I scripts/fin_screen.py   -> results/fins/screen.json + screen.md

Housing (CAD motor_65/build_motor65.py): barrel r 86 from the drive-end face z -52.2 to the rear flange z 67.5;
rear flange r 90 z 67.5..75.5 (cover screws); gland bosses at 12/50.5/72/92 deg, z 49..75, cables radial at z 62.
Existing fins: 10 annular rings, 2.5 mm uniform, r 85.5..94 (8 mm proud), z -43..29, pitch 8 (gap 5.5).
Convection: Elenbaas / Bar-Cohen-Rohsenow isothermal parallel plates (annular fins: channel height L = fin OD;
axial fins: L = fin height, buoyancy x 2/pi for the channel orientation around a horizontal cylinder), bare barrel
Churchill-Chu. Both CALIBRATED on the external-air CFD of the existing housing (scripts/air_h_zones.py).
Tapered fins 4 -> 2.5 mm: efficiency of the equivalent straight fin (mean thickness, corrected length).
Radiation eps 0.7 (make_case.py EMISSIVITY) from the fin-array ENVELOPE (tip surface + open sides), not fin flanks.
"""
import json, math, os
import numpy as np

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "fins"); os.makedirs(W, exist_ok=True)
TW, TA = 373.15, 313.15; DT = TW - TA; TF = (TW + TA) / 2
g, beta, nu, al, kair, Pr = 9.81, 1 / TF, 1.995e-5, 2.82e-5, 0.0293, 0.70
KAL, RHO_AL, CP_AL = 150.0, 2680.0, 900.0
EPS = float(os.environ.get("EPS", 0.1))       # user: bare machined aluminium
HRAD = EPS * 5.670374e-8 * (TW ** 4 - TA ** 4) / DT
R0, Z_F, Z_R = 0.086, -0.04425, 0.0675         # barrel radius, finnable span start (user: z -43..), rear flange [m]
R_MAX = 0.102                                   # user: OD 205 mm overall -> fin tips <= r 102
Z_GL, GL_ARC = 0.04425, 88.0                  # cut-outs r 18 mm round the 4 gland axes (z 62.25; seat r13 + nut/tool room), ~22 deg each
T_B, T_T = 0.004, 0.0025                        # tapered fin base / tip thickness
GAM = g * beta * DT / (nu * al)

# CFD calibration (air case at 3000, T_wall 100 C): fins + channel base, bare barrel; end faces unchanged
CFD = {"fin_h": (0.317 + 0.005) / (1052.4e-4 + 278.6e-4), "bare_h": (0.015 + 0.084) / (37.4e-4 + 222.8e-4),
       "ends_G_conv": 0.182 + 0.159 + 0.037 + 0.015, "ends_A": (332.1 + 271.8 + 74.5 + 37.4) * 1e-4}   # + front strip z<-44


def h_channel(S, L, gfac=1.0):     # Bar-Cohen & Rohsenow, symmetric isothermal plates
    El = gfac * GAM * S ** 4 / L
    return (576 / El ** 2 + 2.873 / El ** 0.5) ** -0.5 * kair / S


def h_cyl(D):                      # Churchill-Chu horizontal cylinder
    Ra = GAM * D ** 3
    return (0.6 + 0.387 * Ra ** (1 / 6) / (1 + (0.559 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2 * kair / D


def eta(h, H, tb, tt):             # straight fin, mean thickness, corrected length
    tm = (tb + tt) / 2; m = math.sqrt(2 * h / (KAL * tm)); Lc = H + tt / 2
    return math.tanh(m * Lc) / (m * Lc)


def annular(zc_list, H, tb, tt, pitch, cal):
    """Annular fins centred at zc_list [m] -> convective G (fins + channel bases), envelope area, volume, span."""
    Ro = R0 + H; G = V = 0.0
    S = pitch - (tb + tt) / 2                                   # mean gap
    h = cal * h_channel(S, 2 * Ro); hb = C_BARE * h_cyl(2 * R0); e = eta(h, H, tb, tt)
    for i, zc in enumerate(zc_list):
        f = (360 - GL_ARC) / 360 if zc + tb / 2 > Z_GL else 1.0     # gland sector cut
        G += h * e * 2 * math.pi * (Ro ** 2 - R0 ** 2) * f + hb * 2 * math.pi * Ro * tt * f   # flanks + tip
        # trapezoidal profile revolved: t(r) = tb - (tb - tt) (r - R0) / H
        V += 2 * math.pi * f * (tb * (Ro ** 2 - R0 ** 2) / 2 - (tb - tt) / H * ((Ro ** 3 - R0 ** 3) / 3 - R0 * (Ro ** 2 - R0 ** 2) / 2))
        if i:
            G += h * 2 * math.pi * R0 * (zc - zc_list[i - 1] - tb) * f   # channel base strip
    span = zc_list[-1] - zc_list[0] + tb
    return G, 2 * math.pi * Ro * span + 2 * math.pi * (Ro ** 2 - R0 ** 2), V, span


def axial(N, H, tb, tt):
    """N straight axial fins over the barrel; the rear part skips the gland sector."""
    S = 2 * math.pi * (R0 + H / 2) / N - (tb + tt) / 2
    h = C_FIN * h_channel(S, H, 2 / math.pi); hb = C_BARE * h_cyl(2 * R0); e = eta(h, H, tb, tt)
    Lz = (Z_R - Z_F) - (Z_R - Z_GL) * GL_ARC / 360             # mean length after the gland cut
    G = N * (h * e * 2 * H * Lz + hb * tt * Lz) + h * (2 * math.pi * R0 - N * tb) * Lz
    V = N * (tb + tt) / 2 * H * Lz
    return G, 2 * math.pi * (R0 + H) * (Z_R - Z_F), V, Z_R - Z_F, S


def total(Gfin, Aenv, span):
    bare = (Z_R - Z_F) - span; hb = C_BARE * h_cyl(2 * R0)
    return Gfin + hb * 2 * math.pi * R0 * bare + CFD["ends_G_conv"], HRAD * (Aenv + 2 * math.pi * R0 * bare + CFD["ends_A"])


C_BARE = CFD["bare_h"] / h_cyl(2 * R0)
ZC0 = [-0.043 + 0.008 * k for k in range(10)]
_g = annular(ZC0, 0.008, 0.0025, 0.0025, 0.008, 1.0)[0]
C_FIN = (CFD["fin_h"] * (1052.4e-4 + 278.6e-4)) / _g         # so the model reproduces the CFD on the CAD fins
V_EXIST = annular(ZC0, 0.008, 0.0025, 0.0025, 0.008, C_FIN)[2]
res = []


def add(name, kind, G, Ae, V, sp, replace=True, **kw):
    Gc, Gr = total(G, Ae, sp); dV = V - V_EXIST if replace else V
    res.append(dict(name=name, kind=kind, UA_WK=round(Gc + Gr, 3), UA_conv=round(Gc, 3), UA_rad=round(Gr, 3),
                    fin_mass_kg=round(V * RHO_AL, 3), d_mass_kg=round(dV * RHO_AL, 3), d_C_kJK=round(dV * RHO_AL * CP_AL / 1e3, 2), **kw))


add("baseline (CAD fins, 2.5 mm uniform)", "baseline", *annular(ZC0, 0.008, 0.0025, 0.0025, 0.008, C_FIN), H_mm=8, pitch_mm=8, n=10)
HS = np.arange(0.008, R_MAX - R0 + 1e-9, 0.002)
for H in HS:                       # tapered rings over the whole span z -44.25..67.5 (cut-outs at the gland bosses)
    for p in np.arange(0.008, 0.0201, 0.0005):
        zc = list(np.arange(Z_F + T_B / 2, Z_R - T_B / 2 + 1e-9, p))
        add(f"ring H{H*1e3:.0f} p{p*1e3:.1f}", "ring tapered", *annular(zc, H, T_B, T_T, p, C_FIN), H_mm=round(H * 1e3), pitch_mm=round(p * 1e3, 1), n=len(zc))
for H in HS:                       # comparison: CAD-style 2.5 mm uniform rings, re-pitched, same span
    for p in np.arange(0.007, 0.0201, 0.0005):
        zc = list(np.arange(Z_F + 0.00125, Z_R - 0.00125 + 1e-9, p))
        add(f"ring uniform2.5 H{H*1e3:.0f} p{p*1e3:.1f}", "ring 2.5 uniform", *annular(zc, H, 0.0025, 0.0025, p, C_FIN), H_mm=round(H * 1e3), pitch_mm=round(p * 1e3, 1), n=len(zc))
for H in HS:                       # axial tapered
    for N in range(24, 121, 2):
        G, Ae, V, sp, S = axial(N, H, T_B, T_T)
        add(f"axial H{H*1e3:.0f} N{N}", "axial tapered", G, Ae, V, sp, H_mm=round(H * 1e3), n=N, gap_mid_mm=round(S * 1e3, 1))

best = {}
for r in res:
    k = (r["kind"], r["H_mm"])
    if k not in best or r["UA_WK"] > best[k]["UA_WK"]:
        best[k] = r
rows = sorted(best.values(), key=lambda r: (r["kind"], r["H_mm"]))
json.dump(dict(eps=EPS, R_max=R_MAX, calibration=dict(C_FIN=C_FIN, C_BARE=C_BARE, h_rad=HRAD, cfd=CFD), best_per_kind_H=rows, all=res),
          open(os.path.join(W, "screen.json"), "w"), indent=1)
md = [f"eps {EPS}, fin tips <= r {R_MAX*1e3:.0f} mm, T_wall 100 C / ambient 40 C\n", "| variant | n | UA W/K (conv + rad) | fin mass kg | d mass kg | d C kJ/K |", "|---|---|---|---|---|---|"]
md += [f"| {r['name']} | {r['n']} | {r['UA_WK']:.2f} ({r['UA_conv']:.2f} + {r['UA_rad']:.2f}) | {r['fin_mass_kg']:.2f} | "
       f"{r['d_mass_kg']:+.2f} | {r['d_C_kJK']:+.2f} |" for r in rows]
open(os.path.join(W, "screen.md"), "w").write("\n".join(md) + "\n")
print(f"C_FIN {C_FIN:.2f}  C_BARE {C_BARE:.2f}  h_rad {HRAD:.2f}")
print("\n".join(md))

"""U666 air CFD -> convective h map for u666_make_case.py --h-file, class means, correlation check.
  python3 u666_air_post.py <air_case> <time> <base_nc> <out.json> [T_wall_K]
Needs <air_case>/<time>/wallHeatFlux + <time>/C (foamPostProcess -func writeCellCentres... or computed here from the mesh) and
<base_nc>/constant/<region>/polyMesh. h_conv = |q|/(Tw-Ta) (radiation is NOT in the air case; make_case adds eps*sigma*(...)).
Classes (housing): fins = r>79 within the fin band z0..z1, end = flat faces (|nz|>0.9) outside the band, body = the rest."""
import json, re, sys, math
import numpy as np
from scipy.spatial import cKDTree
air, time, base, out = sys.argv[1:5]; TW = float(sys.argv[5]) if len(sys.argv) > 5 else 343.15; TA = 313.15
FIN_Z = (-17.8, 92.2)   # K['FIN_C0']-5 .. +PITCH*(N-1)+5

def lst(path, n_re):
    t = open(path).read(); i = t.index("(", t.index(n_re) if n_re in t else 0)
    return t
def read_points(pm):
    t = open(pm + "/points").read(); n = int(re.search(r"\n(\d+)\n\(", t).group(1)); i = t.index("\n(", 0) + 2
    return np.array(re.findall(r"\(([^()\s]+) ([^()\s]+) ([^()\s]+)\)", t[i:]), float)[:n]
def read_faces(pm):
    t = open(pm + "/faces").read(); n = int(re.search(r"\n(\d+)\n\(", t).group(1)); body = t[t.index("\n(") + 2:]
    return [list(map(int, f.split())) for f in re.findall(r"\d+\(([^)]*)\)", body)][:n]
def patch_range(pm, name):
    t = open(pm + "/boundary").read(); m = re.search(name + r"\s*\{[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);", t, re.S)
    return int(m.group(2)), int(m.group(1))
def geom(pm, name):
    P = read_points(pm); F = read_faces(pm); s, n = patch_range(pm, name); C = np.zeros((n, 3)); A = np.zeros(n); N = np.zeros((n, 3))
    for k in range(n):
        v = P[F[s + k]]; c0 = v.mean(0); a = np.zeros(3); cs = np.zeros(3); w = 0
        for j in range(len(v)):
            tri = 0.5 * np.cross(v[j] - c0, v[(j + 1) % len(v)] - c0); ar = np.linalg.norm(tri)
            a += tri; cs += ar * (c0 + v[j] + v[(j + 1) % len(v)]) / 3; w += ar
        C[k] = cs / w if w else c0; A[k] = np.linalg.norm(a); N[k] = a / A[k] if A[k] else 0
    return C, A, N
def patch_values(path, patch):
    t = open(path).read(); i = t.index("boundaryField"); j = re.search(r"\n\s*%s\s*\n\s*\{" % patch, t[i:]).end() + i
    m = re.search(r"value\s+nonuniform\s+List<(scalar|vector)>\s*(\d+)\s*\(", t[j:]); n, st = int(m.group(2)), j + m.end()
    v = np.array(t[st: t.index("\n)", st)].replace("(", " ").replace(")", " ").split(), float)
    return v.reshape(n, -1) if m.group(1) == "vector" else v

q = np.abs(patch_values(f"{air}/{time}/wallHeatFlux", "motor")); h = q / (TW - TA)
xa, Aa, Na = geom(air + "/constant/polyMesh", "motor")
res, cls = {}, {}
tree = cKDTree(xa)
for r in ("housing", "shaft"):
    xs, As, Ns = geom(f"{base}/constant/{r}/polyMesh", "defaultFaces")
    d, k = tree.query(xs); hv = np.where(d > 3e-3, 0.0, h[k]);   # faces >3 mm from the air skin are not external skin: h=0
    print(r, "faces d>3mm:", int((d > 3e-3).sum()), "area cm2", round(float(As[d > 3e-3].sum() * 1e4), 1)); res[r] = {"defaultFaces": hv.tolist()}
    rad = np.hypot(xs[:, 0], xs[:, 1]) * 1e3; zmm = xs[:, 2] * 1e3   # geometry in m, thresholds in mm
    if r == "housing":
        fin = (rad > 79) & (zmm > FIN_Z[0]) & (zmm < FIN_Z[1]); end = ~fin & (np.abs(Ns[:, 2]) > 0.9); body = ~fin & ~end
        groups = {"fins": fin, "end_walls": end, "body": body, "all_housing": np.ones(len(xs), bool)}
    else: groups = {"shaft_stub": np.ones(len(xs), bool)}
    print(f"{r}: {len(xs)} faces, {As.sum()*1e4:.1f} cm2 (air skin {Aa.sum()*1e4:.1f} cm2), map dist max {d.max()*1e3:.2f} mm, mean {np.average(d,weights=As)*1e3:.2f} mm")
    for g, m in groups.items():
        if m.any(): cls[g] = dict(area_cm2=float(As[m].sum() * 1e4), h_mean=float(np.average(hv[m], weights=As[m])), h_min=float(hv[m].min()), h_max=float(hv[m].max()))
        if m.any(): print(f"  {g:12s} area {As[m].sum()*1e4:8.1f} cm2  h_conv mean {cls[g]['h_mean']:.2f}  min {hv[m].min():.2f}  max {hv[m].max():.2f}")
hall = float(np.average(h, weights=Aa)); print(f"air-skin area-weighted h {hall:.2f}; total convective heat {np.sum(q*Aa):.1f} W at dT {TW-TA:.1f} K")
# correlations (air at film T)
Tf = 0.5 * (TW + TA); dT = TW - TA; nu = 1.57e-5 * (Tf / 300) ** 1.7; k = 0.0263 * (Tf / 300) ** 0.8; Pr = 0.71; al = nu / Pr; g = 9.81; be = 1 / Tf
def cc(D): Ra = g * be * dT * D**3 / (nu * al); Nu = (0.6 + 0.387 * Ra ** (1/6) / (1 + (0.559 / Pr) ** (9/16)) ** (8/27)) ** 2; return Nu * k / D, Ra
h_cc_body, Ra1 = cc(0.159); h_cc_env, Ra2 = cc(0.185)                      # bare-cylinder Churchill-Chu: body OD 159, fin tip 185
S, L = 0.0088, 0.185                                                     # fin gap at tip, vertical path
RaS = g * be * dT * S**3 / (nu * al) * S / L; Nu_el = RaS / 24 * (1 - math.exp(-35 / RaS)) ** 0.75; h_el = Nu_el * k / S   # Elenbaas isothermal plates
Sr = 0.0028; RaSr = g * be * dT * Sr**3 / (nu * al) * Sr / L; h_el_root = RaSr / 24 * (1 - math.exp(-35 / RaSr)) ** 0.75 * k / Sr
print(f"correlations: Churchill-Chu D159 {h_cc_body:.2f} (Ra {Ra1:.2e}), D185 {h_cc_env:.2f}; Elenbaas fin channel tip-gap {h_el:.2f}, root-gap {h_el_root:.2f} W/m2K")
json.dump(res, open(out, "w")); json.dump(dict(classes=cls, h_air_skin_mean=hall, T_wall=TW, corr=dict(cc_D159=h_cc_body, cc_D185=h_cc_env, elenbaas_tip=h_el, elenbaas_root=h_el_root)), open(out.replace(".json", "_summary.json"), "w"), indent=1)

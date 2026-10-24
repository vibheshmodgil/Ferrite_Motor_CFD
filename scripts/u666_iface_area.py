"""Coupled-interface area check for a split multi-region case (ascii polyMesh, pure python).
    python3 u666_iface_area.py <case>     -> each A_to_B / B_to_A patch pair: areas (mm2) and mismatch %
"""
import os, re, sys


def body(path):
    s = open(path).read()
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*", "", s)
    return s[s.index("}", s.index("FoamFile")) + 1:]


def lst(path):
    s = body(path)
    i = s.index("(")
    return s[i + 1:s.rindex(")")]


def region_areas(poly):
    pts = [tuple(map(float, p.split())) for p in re.findall(r"\(([^()]*)\)", lst(os.path.join(poly, "points")))]
    fs = lst(os.path.join(poly, "faces"))
    faces = [list(map(int, f.split())) for f in re.findall(r"\d+\(([^()]*)\)", fs)]
    b = body(os.path.join(poly, "boundary"))
    out = {}
    for name, d in re.findall(r"(\w+)\s*\{([^}]*)\}", b):
        n = int(re.search(r"nFaces\s+(\d+)", d).group(1))
        s0 = int(re.search(r"startFace\s+(\d+)", d).group(1))
        a = 0.0
        for f in faces[s0:s0 + n]:
            p0 = pts[f[0]]
            cx = cy = cz = 0.0
            for j in range(1, len(f) - 1):
                u = [pts[f[j]][k] - p0[k] for k in range(3)]
                v = [pts[f[j + 1]][k] - p0[k] for k in range(3)]
                cx += u[1] * v[2] - u[2] * v[1]
                cy += u[2] * v[0] - u[0] * v[2]
                cz += u[0] * v[1] - u[1] * v[0]
            a += 0.5 * (cx * cx + cy * cy + cz * cz) ** 0.5
        out[name] = a * 1e6
    return out


case = sys.argv[1]
A = {r: region_areas(os.path.join(case, "constant", r, "polyMesh"))
     for r in sorted(os.listdir(os.path.join(case, "constant")))
     if os.path.isfile(os.path.join(case, "constant", r, "polyMesh", "boundary"))}
worst = 0.0
for r, ps in A.items():
    for p, a in ps.items():
        m = re.fullmatch(r"(\w+)_to_(\w+)", p)
        if not m or m.group(1) != r or m.group(1) > m.group(2):
            continue
        b = A.get(m.group(2), {}).get(m.group(2) + "_to_" + r)
        err = abs(a - b) / max(a, 1e-30) * 100 if b is not None else float("nan")
        worst = max(worst, err) if b is not None else worst
        print("%-28s %10.1f mm2  partner %10s  mismatch %.3f %%" % (p, a, "%.1f" % b if b is not None else "MISSING", err))
print("worst mismatch %.3f %%" % worst)

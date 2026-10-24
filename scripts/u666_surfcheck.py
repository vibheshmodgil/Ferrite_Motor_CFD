"""Locate the tetgen "PLC Error: a segment and a facet intersect": edge-triangle intersections in a gmsh surface mesh.
    .venv/Scripts/python -I scripts/u666_surfcheck.py mesh/u666/u666_2d.msh      (from u666_mesh.py --solids --2d)
Prints each crossing edge with the two surface tags involved and the point.
"""
import gmsh, os, sys
import numpy as np
from scipy.spatial import cKDTree

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.open(sys.argv[1])
tags, xyz, _ = gmsh.model.mesh.getNodes()
X = np.zeros((int(tags.max()) + 1, 3))
X[tags.astype(int)] = xyz.reshape(-1, 3)
T, S = [], []
for _, s in gmsh.model.getEntities(2):
    for et, _, nt in zip(*gmsh.model.mesh.getElements(2, s)):
        if et == 2:
            t = nt.reshape(-1, 3).astype(int)
            T.append(t); S.append(np.full(len(t), s))
T, S = np.vstack(T), np.concatenate(S)
E = np.unique(np.sort(np.vstack([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1), axis=0)
cen = X[T].mean(1)
rad = np.linalg.norm(X[T] - cen[:, None], axis=2).max(1)
tree = cKDTree(cen)
print("triangles", len(T), "edges", len(E), flush=True)
hits = []
for i0 in (range(0, len(E), 50000) if "--coplanar-only" not in sys.argv else []):
    e = E[i0:i0 + 50000]
    p, q = X[e[:, 0]], X[e[:, 1]]
    mid, half = (p + q) / 2, np.linalg.norm(q - p, axis=1) / 2
    nb = tree.query_ball_point(mid, half + rad.max())
    ei = np.repeat(np.arange(len(e)), [len(n) for n in nb])
    ti = np.concatenate([np.asarray(n, int) for n in nb])
    tv = T[ti]
    ok = ~((tv == e[ei, 0:1]) | (tv == e[ei, 1:2])).any(1)   # no shared vertex
    ei, ti = ei[ok], ti[ok]
    a, b, c = X[T[ti, 0]], X[T[ti, 1]], X[T[ti, 2]]
    o, d = p[ei], q[ei] - p[ei]
    e1, e2 = b - a, c - a
    h = np.cross(d, e2)
    det = (e1 * h).sum(1)
    good = np.abs(det) > 1e-14
    f = np.where(good, 1 / np.where(good, det, 1), 0)
    s_ = o - a
    u = f * (s_ * h).sum(1)
    qv = np.cross(s_, e1)
    v = f * (d * qv).sum(1)
    t = f * (e2 * qv).sum(1)
    eps = 1e-9
    m = good & (u > eps) & (v > eps) & (u + v < 1 - eps) & (t > eps) & (t < 1 - eps)
    for k in np.nonzero(m)[0]:
        ed = e[ei[k]]
        se = sorted(set(S[(T == ed[0]).any(1) & (T == ed[1]).any(1)]))
        hits.append((se, int(S[ti[k]]), np.round(o[k] + t[k] * d[k], 3).tolist()))
print("crossings", len(hits))
for h in hits[:int(os.environ.get("NPRINT", 40))]:
    print("edge of surfaces", h[0], "crosses triangle of surface", h[1], "at", h[2])
# coplanar overlaps (missed above, det ~ 0): mesh nodes lying inside a triangle they do not belong to
used = np.unique(T)
nt = tree.query_ball_point(X[used], rad.max())
hits = []
for i0 in range(0, len(used), 50000):
    nb = nt[i0:i0 + 50000]
    ni = np.repeat(used[i0:i0 + 50000], [len(n) for n in nb])
    ti = np.concatenate([np.asarray(n, int) for n in nb])
    ok = ~(T[ti] == ni[:, None]).any(1)
    ni, ti = ni[ok], ti[ok]
    a, b, c = X[T[ti, 0]], X[T[ti, 1]], X[T[ti, 2]]
    nrm = np.cross(b - a, c - a)
    ar = np.linalg.norm(nrm, axis=1)
    pt = X[ni]
    dist = np.abs(((pt - a) * nrm).sum(1)) / np.maximum(ar, 1e-30)
    w = lambda u, v: (np.cross(u - pt, v - pt) * nrm).sum(1) / np.maximum(ar, 1e-30) ** 2
    l0, l1, l2 = w(b, c), w(c, a), w(a, b)
    m = (ar > 1e-12) & (dist < 1e-6) & (l0 > 1e-6) & (l1 > 1e-6) & (l2 > 1e-6)
    for k in np.nonzero(m)[0]:
        hits.append((int(ni[k]), sorted(set(S[(T == ni[k]).any(1)])), int(S[ti[k]]), np.round(pt[k], 3).tolist()))
print("nodes inside foreign coplanar triangles", len(hits))
for h in hits[:int(os.environ.get("NPRINT", 40))]:
    print("node", h[0], "of surfaces", h[1], "inside triangle of surface", h[2], "at", h[3])

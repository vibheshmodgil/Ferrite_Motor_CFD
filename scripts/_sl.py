import numpy as np, sys
g = sys.argv[1]
L = open("mesh/u666/u666_g_%s.msh" % g).read().split("$Nodes\n")[1]
nn = int(L.split("\n", 1)[0]); lines = L.split("\n")
P = np.array([list(map(float, l.split()[1:4])) for l in lines[1:nn + 1]])
E = L.split("$Elements\n")[1].split("\n")
tri = np.array([list(map(int, l.split()[5:8])) for l in E[1:] if l.split()[1:2] == ["6"] and l.split()[3]]) - 1
a, b, c = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
A = 0.5 * np.abs(np.cross(b - a, c - a)[:, 2])
lmax = np.max([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)], 0)
h = 2 * A / lmax
cen = (a + b + c) / 3
for thr in (0.001, 0.01, 0.05, 0.1):
    print(g, "prisms with min height <", thr, "mm:", int((h < thr).sum()), "of", len(h))
s = np.argsort(h)[:8]
print(np.c_[h[s], np.hypot(cen[s, 0], cen[s, 1]), np.degrees(np.arctan2(cen[s, 1], cen[s, 0])), cen[s, 2]].round(4))
m = h < 0.01
from collections import Counter
print(Counter(zip(np.round(np.hypot(cen[m,0],cen[m,1]),2), np.round(np.degrees(np.arctan2(cen[m,1],cen[m,0])),0))).most_common(6), len(set(np.round(np.degrees(np.arctan2(cen[m,1],cen[m,0])),1))))
print("z levels", sorted(set(np.round(cen[m,2],2)))[:5], "lmax", np.round(lmax[m][:5],3))
rr = np.hypot(P[:, 0], P[:, 1])
k = np.nonzero(m)[0][:6]
print("node r of sliver tris:", [np.round(rr[tri[i]], 4).tolist() for i in k])

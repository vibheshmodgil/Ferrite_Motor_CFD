import gmsh, math
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
occ = gmsh.model.occ
c = occ.importShapes(D + r"\04_coil_65.step")[0][1]
a = occ.importShapes(D + r"\bobbin_A_65.step")[0][1]
b = occ.importShapes(D + r"\bobbin_B_65.step")[0][1]
t = occ.importShapes(D + r"\tooth_65.step")[0][1]
occ.synchronize()
# cross-section of the coil at z = 0 (slot mid-plane): a plane cutting the wire gives one disc per conductor
pl = occ.addRectangle(-40, 40, 0, 80, 45)
cut, _ = occ.intersect([(3, c)], [(2, pl)], removeObject=False, removeTool=True)
occ.synchronize()
cs = sorted((occ.getCenterOfMass(2, f)[0], occ.getCenterOfMass(2, f)[1], occ.getMass(2, f)) for _, f in cut)
print("conductor sections at z=0:", len(cs))
for x, y, A in cs: print(f"  x {x:7.2f} y {y:6.2f} area {A:5.2f} (d_eq {2*math.sqrt(A/math.pi):.2f})")
pts = [(x, y) for x, y, _ in cs]
d = min(math.dist(p, q) for i, p in enumerate(pts) for q in pts[i+1:])
print("min centre distance", round(d, 3), "-> gap", round(d - 2.9, 3))
for name, o in (("bobbinA", a), ("bobbinB", b), ("tooth", t)):
    print(name, "min dist to coil", round(occ.getDistance(3, c, 3, o)[0], 4))
print("bobbin A vs tooth", round(occ.getDistance(3, a, 3, t)[0], 4), " A vs B", round(occ.getDistance(3, a, 3, b)[0], 4))

import gmsh, numpy as np, math
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
h = gmsh.model.occ.importShapes(D+r"\housing.step")[0][1]
c = gmsh.model.occ.importShapes(D+r"\rear_cover.step")[0][1]
gmsh.model.occ.synchronize()
th = math.radians(200)
rs = np.arange(10, 96, 1.0); zs = np.arange(-66, 80, 1.0)
print("     z  " + "".join(f"{int(r)%100:02d}"[1] for r in rs))
for z in zs:
    row = ""
    for r in rs:
        p = [r*math.cos(th), r*math.sin(th), z]
        row += "H" if gmsh.model.isInside(3, h, p) else "C" if gmsh.model.isInside(3, c, p) else "."
    print(f"{z:6.0f}  {row}")

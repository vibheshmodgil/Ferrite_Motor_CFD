import gmsh, json, os, numpy as np
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); occ = gmsh.model.occ
c = [t for d, t in occ.importShapes(os.path.join(D, "04_coil_65.step")) if d == 3][0]
occ.synchronize()
for z in (47.2, 51.0):
    pl = occ.addRectangle(-60, 0, z, 120, 120)
    cut, _ = occ.intersect([(3, c)], [(2, pl)], removeObject=False)
    occ.synchronize()
    print(z, [(round(occ.getCenterOfMass(2, f)[0], 3), round(occ.getCenterOfMass(2, f)[1], 3), round(occ.getMass(2, f), 2)) for _, f in cut])

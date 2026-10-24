import gmsh, json, os, numpy as np
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0); occ = gmsh.model.occ
inst = json.load(open(os.path.join(D, "instances.json")))["instances"]
def place(part):
    out = []
    for i in inst:
        if i["part"] != part: continue
        t = [x for x in occ.importShapes(os.path.join(D, part + ".step")) if x[0] == 3]
        R, tr = np.array(i["R"]), i["t"]
        occ.affineTransform(t, list(np.hstack([R, np.array(tr)[:, None]]).ravel())); out += [x[1] for x in t]
    return out
coils = place("04_coil_65"); plates = place("busbar_L1_65") + place("busbar_L2_65") + place("busbar_L3_65")
straps = place("link_strap_65"); tb = place("terminal_bar_L1") + place("terminal_bar_L2") + place("terminal_bar_L3")
occ.synchronize()
print("plates", len(plates), "straps", len(straps), "tbars", len(tb))
for k, c in enumerate(coils):
    dp = min(occ.getDistance(3, c, 3, p)[0] for p in plates); ds = min(occ.getDistance(3, c, 3, s)[0] for s in straps)
    print(f"coil {k}: to plate {dp:.3f}  to strap {ds:.3f}")
for t in tb: print("tbar to plate", round(min(occ.getDistance(3, t, 3, p)[0] for p in plates), 3))
for t in plates + straps + tb:
    print(t, [round(v, 1) for v in gmsh.model.getBoundingBox(3, t)], round(occ.getMass(3, t)))

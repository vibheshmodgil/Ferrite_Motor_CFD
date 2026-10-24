import gmsh, numpy as np, json
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.occ.importShapes(D+r"\04_coil_65.step"); gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMax", 1.0); gmsh.model.mesh.generate(2)
_, x, _ = gmsh.model.mesh.getNodes(); p = x.reshape(-1,3)
print("z range", p[:,2].min(), p[:,2].max())
for z0 in [-44,-40,-35,-33,0,33,35,40,44,48,52]:
    s = p[abs(p[:,2]-z0)<0.6]
    if len(s): print(f"z={z0:4} n={len(s):5} x[{s[:,0].min():6.1f},{s[:,0].max():6.1f}] y[{s[:,1].min():5.1f},{s[:,1].max():5.1f}]")
s = p[abs(p[:,2])<30]
for y0 in [53,55,58,62,66,70,74,76]:
    t=s[abs(s[:,1]-y0)<0.6]
    if len(t): print(f"y={y0} |x| in [{abs(t[:,0]).min():.1f},{abs(t[:,0]).max():.1f}]")
gmsh.clear(); gmsh.model.occ.importShapes(D+r"\tooth_65.step"); gmsh.model.occ.synchronize()
gmsh.model.mesh.generate(2); _, x, _ = gmsh.model.mesh.getNodes(); q=x.reshape(-1,3); q=q[abs(q[:,2])<1]
for y0 in [53,55,58,62,66,70,74,76,78,80]:
    t=q[abs(q[:,1]-y0)<0.6]
    if len(t): print(f"tooth y={y0} x[{t[:,0].min():.1f},{t[:,0].max():.1f}]")
I=json.load(open(D+r"\instances.json"))["instances"]
for i in I:
    if i["part"] in ("tooth_65","04_coil_65"): print(i["part"], np.round(i["R"],3).tolist(), i["t"]); 

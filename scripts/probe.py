import gmsh, sys, os, time
D = r"C:\Users\vibhe\Downloads\OUTPUT\OUTPUT\cad\motor_65"
parts = ["housing","rear_cover","tooth_65","bobbin_A_65","bobbin_B_65","04_coil_65","rotor_lamination_stack",
         "magnet_ferrite","rotor_end_plate","shaft","bearing_52x30x15"]
gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
for p in parts:
    gmsh.clear(); t=time.time()
    v = gmsh.model.occ.importShapes(os.path.join(D, p+".step")); gmsh.model.occ.synchronize()
    vols=[x for x in v if x[0]==3]
    bb=gmsh.model.getBoundingBox(-1,-1)
    nf=len(gmsh.model.getEntities(2))
    vol=sum(gmsh.model.occ.getMass(3,t_) for _,t_ in vols)
    print(f"{p:24s} vols={len(vols)} faces={nf} vol={vol:9.0f} bb=({bb[0]:.1f},{bb[1]:.1f},{bb[2]:.1f})-({bb[3]:.1f},{bb[4]:.1f},{bb[5]:.1f}) {time.time()-t:.1f}s")

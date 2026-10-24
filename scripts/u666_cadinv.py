import gmsh, sys, json, math
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.option.setNumber("Geometry.OCCImportLabels",1)
gmsh.model.occ.importShapes(sys.argv[1]); gmsh.model.occ.synchronize()
rows=[]
for d,t in gmsh.model.getEntities(3):
    bb=gmsh.model.getBoundingBox(3,t); m=gmsh.model.occ.getMass(3,t)
    rows.append(dict(tag=t,name=gmsh.model.getEntityName(3,t),vol_cm3=round(m/1e3,2),bb=[round(x,1) for x in bb]))
json.dump(rows,open(sys.argv[2],"w"),indent=0)
print(len(rows),"volumes; global bbox",[round(x,1) for x in gmsh.model.getBoundingBox(-1,-1)])

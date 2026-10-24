import gmsh,time
gmsh.initialize(); gmsh.option.setNumber("General.NumThreads",1); gmsh.option.setNumber("General.Terminal",1)
o=gmsh.model.occ; o.importShapes("mesh/u666/housing_simple.brep"); o.synchronize()
V=gmsh.model.getEntities(3); print('solids',len(V))
# exact-feature check
import math
for d,f in gmsh.model.getEntities(2):
    if gmsh.model.getType(d,f)=='Cylinder':
        bb=gmsh.model.getBoundingBox(d,f); r=(bb[3]-bb[0])/2
        if any(abs(r-x)<0.01 for x in (75.0,26.0,17.5)) : print('cyl r=%.2f z %.2f..%.2f'%(r,bb[2],bb[5]))
t=time.time(); o.fragment(V,[]); o.synchronize(); print('fragment',round(time.time()-t,1),flush=True)
gmsh.option.setNumber("Mesh.MeshSizeMax",2.5); gmsh.option.setNumber("Mesh.MeshSizeMin",0.5); gmsh.option.setNumber("Mesh.MeshSizeFromCurvature",0)
gmsh.option.setNumber("Mesh.Algorithm3D",1)
t=time.time(); gmsh.model.mesh.generate(2); print('2D',round(time.time()-t,1),flush=True)
t=time.time(); gmsh.model.mesh.generate(3); print('3D',round(time.time()-t,1))
n=gmsh.model.mesh.getElementsByType(4)[0]; print('tets',len(n))
gmsh.finalize()

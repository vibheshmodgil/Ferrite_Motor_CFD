import gmsh, json, numpy as np
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.merge("mesh/u666/u666_geo.brep"); M=gmsh.model; occ=M.occ; occ.synchronize()
R=json.load(open("mesh/u666/u666_geo.brep.json"))
rank={t:k+1 for k,t in enumerate(sorted(t for ts in R.values() for t in ts))}
R={n:[rank[t] for t in ts] for n,ts in R.items()}; reg={t:n for n,ts in R.items() for t in ts}
from collections import Counter
W=set(R["wedge"])
c=Counter()
for _,f in M.getBoundary([(3,t) for t in W],combined=True,oriented=False):
    up=[reg[u] for u in M.getAdjacencies(2,abs(f))[0] if u not in W]
    if up and up[0]=="stator" and M.getType(2,abs(f))!="Plane":
        c[M.getType(2,abs(f))]+=occ.getMass(2,abs(f))
        if len(str(c))and (globals().__setitem__("k",globals().get("k",0)+1) or k<5):
            g=abs(f); lo,hi=M.getParametrizationBounds(2,g); p=M.getValue(2,g,[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2])
            q=np.array(p)*1.0; cp=M.getClosestPoint(2,g,list(q))[0]
            print(g,M.getType(2,g),"r",np.hypot(p[0],p[1]),"z",p[2],"cp dist",np.linalg.norm(np.array(cp)-q),"inside",M.isInside(2,g,list(cp)), [round(x,2) for x in M.getBoundingBox(2,g)])
print(c)
lab={}
for _,f in M.getBoundary([(3,t) for t in W|set(R["seal"])],combined=True,oriented=False):
    up=[reg[u] for u in M.getAdjacencies(2,abs(f))[0] if u not in W]
    lab[abs(f)]=up[0] if up else "out"
LF=list(lab); LB=np.array([M.getBoundingBox(2,g) for g in LF])
for c in [np.array([7.5*43.5/np.hypot(7.5,42.8),42.8*43.5/np.hypot(7.5,42.8),10.0])]:
    cand=np.nonzero(np.all((c>LB[:,:3]-0.3)&(c<LB[:,3:]+0.3),axis=1))[0]
    for j in cand:
        p=np.array(M.getClosestPoint(2,LF[j],list(c))[0]); print(LF[j],lab[LF[j]],M.getType(2,LF[j]),round(np.linalg.norm(p-c),4),M.isInside(2,LF[j],list(p)),[round(x,1) for x in LB[j]])

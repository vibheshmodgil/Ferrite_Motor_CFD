import gmsh, json, os, numpy as np
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
OUT="mesh/u666"; gmsh.merge(OUT+"/u666_geo.brep"); M=gmsh.model; occ=M.occ; occ.synchronize()
R=json.load(open(OUT+"/u666_geo.brep.json"))
rank={t:k+1 for k,t in enumerate(sorted(t for ts in R.values() for t in ts))}
R={n:[rank[t] for t in ts] for n,ts in R.items()}
reg={t:n for n,ts in R.items() for t in ts}
for n in ["slot","stator","rotor","rpocket","magnets","wedge","seal","endw"]:
    zs=set(); bad=0; nf=[]
    for t in R[n]:
        b=M.getBoundingBox(3,t); L=b[5]-b[2]; V=occ.getMass(3,t)
        bot=[abs(f) for _,f in M.getBoundary([(3,t)],oriented=False) if M.getType(2,abs(f))=="Plane" and abs(M.getBoundingBox(2,abs(f))[2]-b[2])<1e-4 and abs(M.getBoundingBox(2,abs(f))[5]-b[2])<1e-4]
        top=[abs(f) for _,f in M.getBoundary([(3,t)],oriented=False) if M.getType(2,abs(f))=="Plane" and abs(M.getBoundingBox(2,abs(f))[2]-b[5])<1e-4 and abs(M.getBoundingBox(2,abs(f))[5]-b[5])<1e-4]
        A=sum(occ.getMass(2,f) for f in bot); At=sum(occ.getMass(2,f) for f in top)
        ok=abs(A*L-V)<1e-4*V and abs(A-At)<1e-4*A
        bad+= not ok; zs.add((round(b[2],2),round(b[5],2)))
        nb=lambda fs: sorted({reg.get(u,'-') for f in fs for u in M.getAdjacencies(2,f)[0] if u!=t})
        nf.append((len(bot),len(top),tuple(nb(bot)),tuple(nb(top))))
    from collections import Counter
    print(n,len(R[n]),"nonprism",bad,"z",sorted(zs)[:4],Counter(nf).most_common(3),flush=True)
print("----")
for n in ["slot","magnets","wedge","rotor"]:
    for t in R[n]:
        b=M.getBoundingBox(3,t)
        bot=[abs(f) for _,f in M.getBoundary([(3,t)],oriented=False) if abs(M.getBoundingBox(2,abs(f))[5]-M.getBoundingBox(2,abs(f))[2])<1e-3]
        if n!="slot" or not bot or True:
            print(n,t,[round(x,2) for x in b],"V",round(occ.getMass(3,t),1),[(f,M.getType(2,f),round(M.getBoundingBox(2,f)[2],3),round(occ.getMass(2,f),2),[reg.get(u) for u in M.getAdjacencies(2,f)[0] if u!=t]) for f in bot][:6])
            break
print("====")
for t in (76,129,64):
    print(t,[(f,M.getType(2,f),[round(x,2) for x in M.getBoundingBox(2,f)[2::3]],round(occ.getMass(2,f),1),[reg.get(u) for u in M.getAdjacencies(2,f)[0] if u!=t]) for _,f in M.getBoundary([(3,t)],oriented=False)][:14])

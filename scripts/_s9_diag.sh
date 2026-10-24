source /opt/openfoam12/etc/bashrc; cd ~/cfd/u666_air
pkill -x foamRun; sleep 1
postProcess -solver fluid -func writeCellCentres -time 300 > log.cc 2>&1
python3 - <<'PY'
import re,numpy as np
def rd(f,vec):
    s=open(f"300/{f}").read(); i=s.index("internalField"); n=int(re.search(r"List<\w+>\s*(\d+)",s[i:]).group(1)); b=s[i:].split("(",1)[1]
    a=np.array(b.replace("("," ").replace(")"," ").split()[:n*(3 if vec else 1)],float); return a.reshape(n,3) if vec else a
U=rd("U",True); C=rd("C",True)*1e3; T=rd("T",False); m=np.linalg.norm(U,axis=1)
print("T min/max",T.min(),T.max())
for lo,hi in ((0,95),(95,130),(130,200),(200,400)):
    r=np.sqrt(C[:,0]**2+C[:,1]**2+(C[:,2]-30)**2); k=(r>=lo)&(r<hi); print("dist",lo,hi,k.sum(),"Umean",m[k].mean().round(2),"Umax",m[k].max().round(1))
for ax,n in enumerate("xyz"):
    print(n,"U mean by slab",[ (np.round(U[(C[:,ax]>=a)&(C[:,ax]<a+110),ax].mean(),2)) for a in (-330,-220,-110,0,110,220)])
PY

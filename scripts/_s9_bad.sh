source /opt/openfoam12/etc/bashrc; cd ~/cfd/u666_air
mpirun -np 4 postProcess -solver fluid -func writeCellCentres -latestTime -parallel > log.cc 2>&1
python3 - <<'PY'
import re,numpy as np,os
for p in range(4):
    d=f"processor{p}"; ts=sorted((x for x in os.listdir(d) if x.replace('.','').isdigit() and x!='0'),key=float)
    if not ts: continue
    t=ts[-1]
    def rd(f,vec=False):
        s=open(f"{d}/{t}/{f}").read(); i=s.index("internalField"); n=int(re.search(r"List<\w+>\s*(\d+)",s[i:]).group(1)); b=s[i:].split("(",1)[1]
        a=np.array(b.replace("(", " ").replace(")"," ").split()[:n*(3 if vec else 1)],float); return a.reshape(n,3) if vec else a
    T=rd("T"); C=rd("C",True); U=rd("U",True); m=np.linalg.norm(U,axis=1)
    k=np.argsort(T)[:3]; print(p,t,"Tmin",T.min().round(1),"Tmax",T.max().round(1),"Umax",m.max().round(2),"at",C[np.argmax(m)].round(3)*1e3, "Tmin at",C[k[0]].round(3)*1e3)
PY

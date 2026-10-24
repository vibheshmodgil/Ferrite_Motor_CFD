source /opt/openfoam12/etc/bashrc 2>/dev/null; cd ~/cfd/air
ls -la --time-style=full-iso processor0/800/U log.run | awk '{print $7, $9}'
rm -rf 800; reconstructPar -time 800 > log.rec800 2>&1; tail -2 log.rec800; ls -la --time-style=full-iso 800/U | awk '{print $7, $9}'
python3 - <<'PY'
import re, numpy as np
t=open('800/U').read(); i=t.index('internalField'); n=int(re.search(r'List<vector>\s*(\d+)',t[i:]).group(1))
s=t[i:].split('(',1)[1]; v=np.array(s[:s.index(')\n)')+1].replace('(',' ').replace(')',' ').split(),float)[:3*n].reshape(n,3)
m=np.linalg.norm(v,axis=1); print('n',n,'U max %.4f p99 %.4f mean %.5f median %.5f'%(m.max(), np.percentile(m,99), m.mean(), np.median(m)))
c=open('constant/polyMesh/points').read()[:0]
PY
grep -m3 -n "Uy\|Ux" log.run | head -3

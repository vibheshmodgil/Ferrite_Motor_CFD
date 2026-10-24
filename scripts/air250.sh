until [ -d ~/cfd/air/processor0/200 ] || grep -q "FATAL" ~/cfd/air/log.run 2>/dev/null; do sleep 30; done
grep -A4 FATAL ~/cfd/air/log.run | head -6
source /opt/openfoam12/etc/bashrc 2>/dev/null; cd ~/cfd/air
reconstructPar -time 200 > /dev/null 2>&1
python3 - <<'PY'
import re, numpy as np
t=open('200/U').read(); i=t.index('internalField'); n=int(re.search(r'List<vector>\s*(\d+)',t[i:]).group(1))
s=t[i:].split('(',1)[1]; v=np.array(s[:s.index(')\n)')+1].replace('(',' ').replace(')',' ').split(),float)[:3*n].reshape(n,3)
m=np.linalg.norm(v,axis=1); print('iteration 200: U max %.3f m/s  p99 %.3f  mean %.4f'%(m.max(), np.percentile(m,99), m.mean()))
PY
rm -rf 200

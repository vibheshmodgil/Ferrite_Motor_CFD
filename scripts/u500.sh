cd ~/cfd/inair_continuous
python3 - <<'PY'
import re, numpy as np
t=open('500/U').read(); i=t.index('internalField'); n=int(re.search(r'List<vector>\s*(\d+)',t[i:]).group(1))
s=t[i:].split('(',1)[1]; v=np.array(s[:s.index(')\n)')+1].replace('(',' ').replace(')',' ').split(),float)[:3*n].reshape(n,3)
m=np.linalg.norm(v,axis=1); print('U max %.2f  p99 %.2f  mean %.2f m/s  (rotor tip speed 16.6 m/s)'%(m.max(),np.percentile(m,99),m.mean()))
PY

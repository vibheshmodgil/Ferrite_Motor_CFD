source /opt/openfoam12/etc/bashrc 2>/dev/null
cd ${AIRC:-~/cfd/u666_air}
foamPostProcess -solver fluid -func "patchIntegrate(patch=motor, fields=(T))" -latestTime 2>&1 | grep -iE "integral|areaInt|=" | tail -4
foamPostProcess -solver fluid -func "patchAverage(patch=motor, fields=(T))" -latestTime 2>&1 | grep -iE "average|=" | tail -4
python3 - <<'PY'
import re, numpy as np
import os, sys
lt=max((d for d in os.listdir('.') if d.replace('.','').isdigit()), key=float)
t=open(lt+'/U').read(); i=t.index('internalField'); n=int(re.search(r'List<vector>\s*(\d+)',t[i:]).group(1))
s=t[i:].split('(',1)[1]; v=np.array(s[:s.index(')\n)')+1].replace('(',' ').replace(')',' ').split(),float)[:3*n].reshape(n,3)
m=np.linalg.norm(v,axis=1); print('U max %.3f m/s  p99 %.3f  mean %.3f'%(m.max(), np.percentile(m,99), m.mean()))
sys.exit(1 if (np.percentile(m,99) > 0.8 or m.max() > 5.0) else 0)   # KNOWN_ISSUES 12: U max > 5 m/s = non-physical   # buoyancy velocity scale sqrt(g beta dT L) ~ 0.57 m/s
PY

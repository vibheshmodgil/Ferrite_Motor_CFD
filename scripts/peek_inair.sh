cd ~/cfd/base_solids/constant/inair/polyMesh
python3 - <<'PY'
import re
t=open('boundary').read()
for m in re.finditer(r'\n    (\w+)\n    \{(.*?)\n    \}', t, re.S):
    b=m.group(2); print(m.group(1), re.search(r'type\s+(\w+)',b).group(1), re.search(r'nFaces\s+(\d+)',b).group(1))
PY
grep -c . ~/cfd/base_solids/constant/inair/polyMesh/owner >/dev/null; head -c 600 ~/cfd/base_solids/constant/inair/polyMesh/owner | grep -ao "nCells:[0-9]*"
ls ~/cfd/continuous/processor0 | sort -n | tail -3

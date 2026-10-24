cd ~/cfd/inair_continuous; LT=$(ls -d [0-9]* | sort -n | tail -1); echo "time $LT"
python3 - $LT <<'PY'
import re, sys, numpy as np
lt = sys.argv[1]
def internal(name, vec=False):
    t = open(f"{lt}/{name}").read(); i = t.index("internalField")
    m = re.search(r"List<(scalar|vector)>\s*(\d+)", t[i:]); n = int(m.group(2))
    s = t[i:].split("(", 1)[1]
    v = np.array(s[:s.index(")\n)") + 1 if vec else s.index("\n)")].replace("(", " ").replace(")", " ").split(), float)
    return v[:3*n].reshape(n, 3) if vec else v[:n]
T = internal("T"); U = internal("U", True)
# volume weights: use cell volumes if written, else plain mean
print("air T mean %.2f K (%.1f C), min %.1f, max %.1f C" % (T.mean(), T.mean()-273.15, T.min()-273.15, T.max()-273.15))
m = np.linalg.norm(U, axis=1); print("U max %.2f, p99 %.2f, mean %.2f m/s" % (m.max(), np.percentile(m, 99), m.mean()))
PY

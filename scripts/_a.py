import re,sys
reg=sys.argv[1]
for p in range(4):
    f=open(f"/home/cfd/cfd/u666_etest/processor{p}/10/{reg}/T").read()
    m=re.search(r"internalField\s+nonuniform List<scalar>\s*(\d+)\s*\(",f)
    if not m: print(p,"uniform"); continue
    n=int(m.group(1)); a=f[m.end():].split(")")[0].split()
    v=list(map(float,a))
    bad=[i for i,x in enumerate(v) if x>330]
    print(p,n,"max",max(v),"nbad",len(bad),"first",bad[:5])

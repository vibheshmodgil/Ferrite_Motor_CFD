# Write a cellZones file in which zones named in argv[3:] are merged into one zone argv[2].
# python3 merge_zones.py <cellZones in> <out> <merged name> <zone> <zone> ...   (ascii cellZoneList)
import re, sys
src, out, name, parts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
txt = open(src).read()
zones = {m.group(1): list(map(int, m.group(3).split()))
         for m in re.finditer(r"\n(\w+)\s*\{\s*type cellZone;\s*cellLabels\s+List<label>\s*(\d+)\s*\(([^)]*)\)", txt)}
assert set(parts) <= set(zones), (parts, list(zones))
new = {k: v for k, v in zones.items() if k not in parts}
new[name] = sorted(c for p in parts for c in zones[p])
assert sum(map(len, new.values())) == sum(map(len, zones.values()))
with open(out, "w") as f:
    f.write("FoamFile { format ascii; class cellZoneList; location \"constant/polyMesh\"; object cellZones; }\n%d\n(\n" % len(new))
    for k, v in new.items():
        f.write("%s\n{\n    type cellZone;\ncellLabels List<label> %d\n(\n%s\n)\n;\n}\n" % (k, len(v), "\n".join(map(str, v))))
    f.write(")\n")
print({k: len(v) for k, v in new.items()})

"""Turn a region's defaultFaces patch into a wall (so wallHeatFlux reports it). python3 wallify.py <boundary file>"""
import re, sys
f = sys.argv[1]
t = open(f).read()
t = re.sub(r"(\n    defaultFaces\n    \{[^}]*?type\s+)patch;", r"\1wall;", t)
open(f, "w").write(t)

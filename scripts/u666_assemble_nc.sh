# U666 NON-CONFORMAL base (route B, MESH2): per-region gmsh meshes (u666_mesh.py --solids --group G -> u666_g_G.msh)
# -> ~/cfd/<base>/constant/<G>/polyMesh. Patches <G>_to_<nb> become mappedWall, method intersection (OF12 AMI),
# "outside" becomes defaultFaces (wall). cellZones (slot/endw, rotor/rpocket, ...) are kept from the physical volumes.
#   bash u666_assemble_nc.sh [base_dir]      (default ~/cfd/u666_base_nc) ; then checkMesh per region
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); M=$S/../mesh/u666; B=${1:-~/cfd/u666_base_nc}
G="housing inair stator winding wedge rotor magnets endcaps shaft bearings"
rm -rf $B; mkdir -p $B/system $B/constant
cat > $B/system/controlDict <<CD
FoamFile { format ascii; class dictionary; object controlDict; }
application foamMultiRun; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 8; timeFormat general;
CD
for g in $G; do
  T=$B/tmp_$g; mkdir -p $T/system $T/constant; cp $B/system/controlDict $T/system/
  (cd $T && gmshToFoam $M/u666_g_$g.msh > log.gmshToFoam 2>&1 && transformPoints "scale=(1e-3 1e-3 1e-3)" > log.transform 2>&1)
  rm -rf $T/constant/polyMesh/sets; mkdir -p $B/constant/$g; mv $T/constant/polyMesh $B/constant/$g/polyMesh
  cp $T/log.gmshToFoam $B/log.gmshToFoam.$g; rm -rf $T
done
python3 - $B <<'PY'
import re, sys, os
B = sys.argv[1]
for r in sorted(os.listdir(B + "/constant")):
    f = f"{B}/constant/{r}/polyMesh/boundary"
    t = open(f).read()
    def sub(m):
        name, body = m.group(1), m.group(2)
        mm = re.fullmatch(r"(\w+)_to_(\w+)", name)
        nf, sf = re.search(r"nFaces\s+\d+;", body).group(0), re.search(r"startFace\s+\d+;", body).group(0)
        if mm:
            return (f"    {name}\n    {{\n        type mappedWall;\n        inGroups List<word> 1(wall);\n"
                    f"        matchTolerance 0.5;\n        method intersection;   // OF12 name of the AMI (nearestPatchFaceAMI) coupling\n        sampleRegion {mm.group(2)};\n"
                    f"        samplePatch {mm.group(2)}_to_{mm.group(1)};\n        {nf}\n        {sf}\n    }}")
        if name == "outside":
            return f"    defaultFaces\n    {{\n        type wall;\n        inGroups List<word> 1(wall);\n        {nf}\n        {sf}\n    }}"
        return m.group(0)
    t = re.sub(r"    (\w+)\n    \{([^}]*)\}", sub, t)
    open(f, "w").write(t)
    print(r, re.findall(r"^    (\w+)\n", t, re.M))
PY

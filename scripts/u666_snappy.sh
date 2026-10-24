# U666 solids mesh with snappyHexMesh (multi-region by cellZones) from the gmsh 2D STLs (u666_mesh.py --solids --stl).
#   bash u666_snappy.sh [case=~/cfd/u666_snappy]     knobs: H (background cell, mm, 2.5), LV_<region>="min max"
# STLs are in mm: the mesh is built in mm and scaled to m at the end. skin.stl (no zone) cuts away the outside;
# each <region>.stl (closed) gives cellZone <region> (mode inside). Outside patch renamed defaultFaces (make_case).
# Then: bash u666_prep_base.sh <case> ~/cfd/u666_base   (a directory argument = use its polyMesh, no gmshToFoam)
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); C=${1:-$HOME/cfd/u666_snappy}; H=${H:-2.5}
STL=$S/../mesh/u666/stl
rm -rf $C; mkdir -p $C/system $C/constant/triSurface
cp $STL/*.stl $C/constant/triSurface/
cd $C
cat > system/controlDict <<CD
FoamFile { format ascii; class dictionary; object controlDict; }
application snappyHexMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 10; timeFormat general;
CD
cat > system/fvSchemes <<CD
FoamFile { format ascii; class dictionary; object fvSchemes; }
ddtSchemes {} gradSchemes {} divSchemes {} laplacianSchemes {} interpolationSchemes {} snGradSchemes {}
CD
cat > system/fvSolution <<CD
FoamFile { format ascii; class dictionary; object fvSolution; }
CD
cat > system/meshQualityDict <<CD
FoamFile { format ascii; class dictionary; object meshQualityDict; }
#includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"
CD
python3 - $H <<'PY'
import sys, glob, os, numpy as np
H = float(sys.argv[1])
v = np.array([l.split()[1:4] for l in open("constant/triSurface/skin.stl") if l.lstrip().startswith("vertex")], float)
lo, hi = v.min(0) - 2 * H, v.max(0) + 2 * H
n = np.ceil((hi - lo) / H).astype(int)
hi = lo + n * H
pts = " ".join("(%g %g %g)" % (x, y, z) for z in (lo[2], hi[2]) for x, y in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])))
open("system/blockMeshDict", "w").write("""FoamFile { format ascii; class dictionary; object blockMeshDict; }
convertToMeters 1;
vertices (%s);
blocks (hex (0 1 2 3 4 5 6 7) (%d %d %d) simpleGrading (1 1 1));
boundary ( box { type patch; faces ((0 3 2 1) (4 5 6 7) (0 1 5 4) (2 3 7 6) (1 2 6 5) (0 4 7 3)); } );
""" % (pts, *n))
# refinement levels (min max) per region surface; level 1 = H/2, 2 = H/4, 3 = H/8. CALIBRATION/size KNOB (LV_<region>)
LV = dict(wedge=(2, 2), seal=(2, 2), rpocket=(1, 2))    # all others (1 1); (1 2)/level-3 everywhere -> 8 M cells, 8 GB
regs = sorted(os.path.basename(f)[:-4] for f in glob.glob("constant/triSurface/*.stl"))
lv = lambda r: tuple(int(x) for x in os.environ.get("LV_" + r, "%d %d" % LV.get(r, (1, 1))).split())
geo = "\n".join("    %s { type triSurfaceMesh; file \"%s.stl\"; }" % (r, r) for r in regs)
ref = []
for r in regs:
    a, b = lv(r)
    if r == "skin":
        ref.append("        skin { level (%d %d); patchInfo { type wall; } }" % (a, b))
    else:
        ref.append("        %s { level (%d %d); faceZone %s; cellZone %s; mode inside; }" % (r, a, b, r, r))
# volume refinement of the thin zones (their whole inside at the max level)
vref = "\n".join("        %s { mode inside; level %d; }" % (r, lv(r)[1]) for r in regs if r != "skin" and lv(r)[1] >= 2 and r in ("wedge", "seal"))
open("system/snappyHexMeshDict", "w").write("""FoamFile { format ascii; class dictionary; object snappyHexMeshDict; }
#includeEtc "caseDicts/mesh/generation/snappyHexMeshDict.cfg"
castellatedMesh true; snap true; addLayers false;
geometry
{
%s
};
castellatedMeshControls
{
    maxLocalCells 4000000; maxGlobalCells 4000000; nCellsBetweenLevels 1; resolveFeatureAngle 30;
    refinementSurfaces
    {
%s
    }
    refinementRegions
    {
%s
    }
    insidePoint (70.3 0.11 30.07);   // stator yoke (r 70.3: slot bottom 65.5, OD 75; stack z -0.35..60.2)
}
snapControls { nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 10;
               implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false; }
writeFlags (); mergeTolerance 1e-6;
""" % (geo, "\n".join(ref), vref))
PY
blockMesh > log.blockMesh 2>&1
snappyHexMesh -overwrite > log.snappy 2>&1
grep -E "^Finished|Layer mesh|cells:" log.snappy | tail -3
transformPoints "scale=(1e-3 1e-3 1e-3)" > log.transform 2>&1
sed -i 's/^\(\s*\)skin$/\1defaultFaces/' constant/polyMesh/boundary
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Max non-orth|skewness|Mesh OK|Failed|\*\*\*" log.checkMesh
# region volumes (cm3) for the +-3 % gate vs mesh/u666/stl/volumes.json: run after u666_prep_base.sh, e.g.
#   for r in $(ls -d constant/*/polyMesh | cut -d/ -f2); do checkMesh -region $r | grep 'Total volume'; done

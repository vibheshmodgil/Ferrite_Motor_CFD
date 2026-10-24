# 3D fields for the 3D views -> results/vtk3d/<name>/<region>.vtk (legacy binary, internal cells only)
#   bash export3d.sh solid <case> <time>      every solid region of a thermal case
#   bash export3d.sh fluid <case>             a single-region fluid case at its latest time
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/vtk3d
kind=$1; C=~/cfd/$2; cd $C
if [ $kind = solid ]; then
  T=$3; O=$W/$2_$T; mkdir -p $O
  [ -d $T ] || reconstructPar -allRegions -time $T > log.rec3d 2>&1
  for r in $(ls -d constant/*/polyMesh | cut -d/ -f2); do
    [ $r = inair ] && continue
    rm -rf VTK/$r; foamToVTK -region $r -time $T -noFaceZones -noPointValues > log.vtk_$r 2>&1
    f=$(find VTK/$r -maxdepth 1 -name "*.vtk" | head -1); [ -n "$f" ] && cp "$f" $O/$r.vtk
  done
else
  T=$(foamListTimes -latestTime | tail -1); O=$W/$2; mkdir -p $O
  rm -rf VTK; foamToVTK -time $T -noFaceZones -noPointValues -fields '(U T)' > log.vtk 2>&1
  f=$(find VTK -maxdepth 1 -name "*.vtk" | head -1); [ -n "$f" ] && cp "$f" $O/internal.vtk
fi
ls -la $O

# section planes of T for the report: bash slices.sh <case> <time>   -> results/<case>/slices/<region>_{z,x}.vtk
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
# optional 3rd arg: radial-plane position z in metres (default 0.005); a non-default z gets its own folder
C=~/cfd/$1; T=$2; Z=${3:-0.005}; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/$1/slices_$T
[ "$Z" != "0.005" ] && W=${W}_z$Z
cd $C; mkdir -p $W
[ -d $T ] || reconstructPar -allRegions -time $T > log.reconstruct_$T 2>&1; touch log.reconstruct_$T
for r in $(ls -d constant/*/polyMesh | cut -d/ -f2); do
  for ax in z x; do
    n=$([ $ax = z ] && echo "(0 0 1)" || echo "(1 0 0)"); p=$([ $ax = z ] && echo "(0 0 $Z)" || echo "(0 0 0)")
    rm -rf postProcessing/$r/cutPlaneSurface*
    foamPostProcess -region $r -func "cutPlaneSurface(point=$p, normal=$n, T)" -time $T > log.slice_${r}_$ax 2>&1
    f=$(find postProcessing/$r -path "*cutPlaneSurface*" -path "*/$T/*" -name "*.vtk" | head -1)
    [ -n "$f" ] && cp "$f" $W/${r}_$ax.vtk
  done
done
ls $W

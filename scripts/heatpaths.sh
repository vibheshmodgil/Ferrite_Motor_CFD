# Heat crossing every patch of every region at one time: bash heatpaths.sh <case> <time>
#   -> results/<case>/heatflow_<time>.txt   (region patch Q[W], positive = into the region)
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
C=~/cfd/$1; T=$2; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/$1; mkdir -p $W
cd $C; [ -d $T ] || reconstructPar -allRegions -time $T > log.rec_$T 2>&1
out=$W/heatflow_$T.txt; : > $out
for r in $(ls -d constant/*/polyMesh | cut -d/ -f2); do
  # count the outer skin / cut faces too: wallHeatFlux only reports wall patches
  python3 $(dirname $(readlink -f $0))/wallify.py constant/$r/polyMesh/boundary
  rm -rf postProcessing/$r/wallHeatFlux
  foamPostProcess -solver solid -region $r -func wallHeatFlux -time $T > log.whf_$r 2>&1
  f=$(find postProcessing/$r/wallHeatFlux -name "wallHeatFlux.dat" | head -1)
  [ -n "$f" ] && grep -v "^#" $f | awk -v r=$r '{print r, $2, $5}' >> $out
done
cat $out

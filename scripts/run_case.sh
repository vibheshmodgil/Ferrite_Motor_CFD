# bash run_case.sh <loadpoint> [endTime-override]   -> $HOME/cfd/<loadpoint>, runs on 4 cores
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); C=$HOME/cfd/${PREFIX}$1${SUFFIX}   # SUFFIX: rerun under a new case name
python3 $S/make_case.py ${BASE:-$HOME/cfd/base_solids} $C $1 ${HFILE:+--h-file $HFILE} || exit 1
cd $C
[ -n "$2" ] && sed -i "s/^endTime .*/endTime         $2;/" system/controlDict
[ -n "$WRITE" ] && sed -i "s/^writeInterval .*/writeInterval   $WRITE;/" system/controlDict
decomposePar -allRegions > log.decompose 2>&1 || { tail -20 log.decompose; exit 1; }
mpirun -np ${NP:-4} foamMultiRun -parallel > log.run 2>&1
tail -5 log.run

# U666 energy-conservation test: adiabatic skin, fixed dummy losses (u666_loadpoints.json "etest"), 300 s.
# Exact: sum(rho cv dT dV) = Q_total x t.   [BASE=~/cfd/u666_base NP=4] bash u666_energy_test.sh [name]
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); C=$HOME/cfd/u666_etest${1:+_$1}
ADIABATIC=1 JOULE_TC=0 python3 $S/u666_make_case.py ${BASE:-$HOME/cfd/u666_base} $C etest --lp-file $S/../u666_loadpoints.json || exit 1
cd $C
decomposePar -allRegions > log.decompose 2>&1 || { tail -20 log.decompose; exit 1; }
mpirun -np ${NP:-4} foamMultiRun -parallel > log.run 2>&1
tail -3 log.run
python3 $S/u666_energy_balance.py $C etest $S/../u666_loadpoints.json

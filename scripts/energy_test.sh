# Energy-conservation test of the thermal model: adiabatic outer skin, fixed losses, 300 s.
# Exact answer: sum(rho cv dT dV) = Q_total x 300 s.   [BASE=<base_dir>] bash energy_test.sh <name> [ISO_STEEL k]
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); C=$HOME/cfd/etest_$1
ADIABATIC=1 JOULE_TC=0 ISO_STEEL=$2 python3 $S/make_case.py ${BASE:-$HOME/cfd/base_solids} $C continuous || exit 1
cd $C
sed -i 's/^endTime .*/endTime         300;/; s/^deltaT .*/deltaT          10;/; s/^writeInterval .*/writeInterval   300;/' system/controlDict
[ -n "$NOUTER" ] && sed -i "s/nOuterCorrectors .*/nOuterCorrectors $NOUTER;/" system/fvSolution
[ -n "$DTT" ] && sed -i "s/^deltaT .*/deltaT          $DTT;/" system/controlDict
[ -n "$ETEND" ] && sed -i "s/^endTime .*/endTime         $ETEND;/; s/^writeInterval .*/writeInterval   $ETEND;/" system/controlDict
decomposePar -allRegions > log.decompose 2>&1 && mpirun -np 4 foamMultiRun -parallel > log.run 2>&1
tail -2 log.run
bash $S/energy_check.sh etest_$1 0 ${ETEND:-300}

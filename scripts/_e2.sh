# BASE2 energy test: assemble prism base, make adiabatic duty1 case, run. env DT N END WIND_ISO ASM=1
source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
B=~/cfd/u666_base_nc; C=~/cfd/u666_e2
if [ "${ASM:-0}" = 1 ]; then
  bash $S/u666_assemble_nc.sh $B > ~/cfd/log.assemble2 2>&1 || exit 1
  for r in $(ls $B/constant); do echo "$r $(checkMesh -case $B -region $r 2>&1 | grep -E 'cells:|Mesh OK|Failed|\*\*\*' | tr '\n' ' ')"; done > ~/cfd/log.check2
  python3 $S/u666_iface_area.py $B > ~/cfd/log.iface2 2>&1
fi
[ "${RUN:-1}" = 0 ] && exit 0
ADIABATIC=1 JOULE_TC=0 $XENV python3 $S/u666_make_case.py $B $C duty1 > ~/cfd/log.make2 2>&1 || exit 1
cd $C
sed -i "s/^endTime .*/endTime ${END:-60};/; s/^deltaT .*/deltaT ${DT:-1};/; s/^writeInterval .*/writeInterval ${END:-60};/" system/controlDict
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors ${N:-3}/" system/fvSolution
decomposePar -allRegions > log.decompose 2>&1
date +%s > t_start
mpirun -np 4 foamMultiRun -parallel > log.run 2>&1
date +%s > t_end
ADIAB=1 python3 $S/u666_energy_balance.py $C duty1 x > log.balance 2>&1

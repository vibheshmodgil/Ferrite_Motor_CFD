# U666 duty1..5 sequential chain on the nc solid base. Run detached: tmux new -d -s duty 'bash scripts/u666_duty_chain.sh'
#   env: H=h-file (default ~/cfd/u666_air_h.json)  SMOKE=1 -> duty1 20 s only, case u666_smoke
#   dt 1 s, nOuter 3, T0 = ambient 40 C, eps 0.1. Probe/flux every 10 s. Cases ~/cfd/u666_duty<i>, log ~/cfd/duty_chain.log
source /opt/openfoam12/etc/bashrc
unset FOAM_SIGFPE
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; B=~/cfd/u666_base_nc; H=${H:-$HOME/cfd/u666_air_h.json}
LOG=~/cfd/duty_chain.log
run() {  # name loadpoint end_s
  C=~/cfd/$1; echo "$(date) START $1 $2 end=$3 s" >> $LOG
  rm -rf $C; EMISSIVITY=0.1 python3 $S/u666_make_case.py $B $C $2 --h-file $H > ~/cfd/log.make_$1 2>&1 || { echo "$(date) MAKE FAIL $1" >> $LOG; return 1; }
  cd $C
  sed -i "s/^endTime .*/endTime $3;/; s/^deltaT .*/deltaT 1;/; s/^writeInterval .*/writeInterval $4;/" system/controlDict
  sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors 3/" system/fvSolution
  decomposePar -allRegions > log.decompose 2>&1
  date +%s > t_start
  mpirun -np 4 foamMultiRun -parallel > log.run 2>&1; rc=$?
  date +%s > t_end; echo "$(date) END $1 rc=$rc" >> $LOG
  [ $rc = 0 ] && grep -q "^ *End" log.run
}
if [ "${SMOKE:-0}" = 1 ]; then run u666_smoke duty1 20 20; exit $?; fi
i=0
for spec in "duty1 300" "duty2 900" "duty3 1800" "duty4 2700" "duty5 2700"; do
  set -- $spec; run u666_$1 $1 $2 30 || echo "$(date) $1 FAILED, continuing" >> $LOG
done
echo "$(date) CHAIN DONE" >> $LOG

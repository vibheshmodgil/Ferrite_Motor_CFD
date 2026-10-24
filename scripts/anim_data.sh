# Snapshots for the temperature-rise and heat-transfer animations (runs in tmux "anim", single core except the rerun)
#  1. continuous: section planes + heat-path audit at every saved time (0.5 h steps to 5 h, then 1 h to 12 h)
#  2. peak torque: rerun saving every 10 s (after the internal-air CFD has freed the CPU), then planes + heat paths
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
echo "== continuous $(date)"
for t in $(ls ~/cfd/continuous/processor0 | grep -E '^[0-9]+$' | sort -n); do
  [ "$t" = 0 ] && continue
  [ -d $W/continuous/slices_$t ] || bash $S/slices.sh continuous $t > /dev/null 2>&1
  [ -f $W/continuous/heatflow_$t.txt ] || bash $S/heatpaths.sh continuous $t > /dev/null 2>&1
  echo "  $t"
done

echo "== waiting for the internal-air CFD to finish $(date)"
while tmux has-session -t inair2 2>/dev/null; do sleep 60; done

echo "== peak torque rerun, writes every 10 s $(date)"
A=~/cfd/peak_torque_anim
if [ ! -f $A/done ]; then
  rm -rf $A; cp -r ~/cfd/peak_torque $A; cd $A
  for p in processor*; do (cd $p; ls | grep -E '^[0-9.]+$' | grep -vx 0 | xargs -r rm -rf); done
  ls | grep -E '^[0-9.]+$' | grep -vx 0 | xargs -r rm -rf
  rm -rf postProcessing log.*
  sed -i 's/^writeInterval .*/writeInterval   10;/' system/controlDict
  mpirun -np 4 foamMultiRun -parallel > log.run 2>&1 && touch done
fi
for t in $(seq 10 10 250); do
  [ -d $W/peak_torque_anim/slices_$t ] || bash $S/slices.sh peak_torque_anim $t > /dev/null 2>&1
  [ -f $W/peak_torque_anim/heatflow_$t.txt ] || bash $S/heatpaths.sh peak_torque_anim $t > /dev/null 2>&1
done
mkdir -p $W/peak_torque_anim && cp -r $A/postProcessing $W/peak_torque_anim/ 2>/dev/null
echo "ANIM_DATA_DONE $(date)"

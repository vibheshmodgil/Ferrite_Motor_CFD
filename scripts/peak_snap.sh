# peak-torque snapshots from the existing run (every 50 s) for its animations; no re-run
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
for t in 50 100 150 200 250; do
  [ -d $W/peak_torque/slices_$t ] || bash $S/slices.sh peak_torque $t > /dev/null 2>&1
  [ -f $W/peak_torque/heatflow_$t.txt ] || bash $S/heatpaths.sh peak_torque $t > /dev/null 2>&1
  echo "  $t"
done
echo PEAK_SNAP_DONE

# Detailed reruns with fine field writes for the 3D viewer, under new case names (nothing existing is touched),
# with the baseline post: slices at every write, heatflow + export3d at the end, energy balance.
#   tmux new-session -d -s viz "bash viz_runs.sh > ~/cfd/viz.log 2>&1"     -> ~/cfd/<case>, results/viz/<case>
# End times sit on the write grid (OpenFOAM writes no fields at an off-grid endTime).
# duty2/3/5 have no earlier detailed run, so their post is also copied to results/detailed/<lp> for the comparison.
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; R=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results; W=$R/viz
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
while tmux has-session -t q35 2>/dev/null; do sleep 60; done
# lp endTime writeInterval case
for spec in "duty2 1350 90 det_duty2_viz" "duty3 2700 180 det_duty3_viz" "duty1 480 30 det_duty1_viz" \
            "duty4 1680 120 det_duty4_viz" "duty5 4080 240 det_duty5_viz" "duty4 1680 120 duty4_viz"; do
  set -- $spec; lp=$1; tend=$2; C=$4
  echo "=== $(date '+%F %T') $C"
  if [ ${C:0:4} = det_ ]; then
    BASE=~/cfd/base_detailed PREFIX=det_ SUFFIX=_viz HFILE=~/cfd/h_cfd_detailed.json WRITE=$3 bash $S/run_case.sh $lp $tend
  else
    SUFFIX=_viz HFILE=~/cfd/h_cfd.json WRITE=$3 bash $S/run_case.sh $lp $tend
  fi
  cd ~/cfd/$C; grep -q "^[[:space:]]*End$" log.run || { echo "$C RUN FAILED"; continue; }
  reconstructPar -allRegions > log.reconstruct 2>&1
  rm -rf $W/$C; mkdir -p $W/$C; cp -r postProcessing $W/$C/
  bash $S/energy_check.sh $C 0 $tend > $W/$C/energy_T.txt
  python3 $S/energy_balance.py viz/$C $lp
  for t in $(ls -d [0-9]* | grep -vx 0); do bash $S/slices.sh $C $t > /dev/null 2>&1; done
  bash $S/heatpaths.sh $C $tend > /dev/null 2>&1
  bash $S/export3d.sh solid $C $tend > /dev/null 2>&1
  mv $R/$C/* $W/$C/ && rmdir $R/$C; mv $R/vtk3d/${C}_$tend $W/$C/vtk3d_$tend
  case $C in det_duty[235]_viz) rm -rf $R/detailed/$lp; cp -r $W/$C $R/detailed/$lp; touch $R/detailed/$lp/done;; esac
  echo "=== $(date '+%F %T') $C ready"
done
echo "=== $(date '+%F %T') VIZ DONE"

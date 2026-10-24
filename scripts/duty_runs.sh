# Design9795_1 duty points: transient run -> results/<lp>/ (postProcessing, sections, heat paths, 3D, energy balance).
#   tmux new-session -d -s duty "bash duty_runs.sh duty4:5400:$(seq -s: 900 900 5400) > ~/cfd/duty.log 2>&1"   (lp:endTime:post times)
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
for spec in "$@"; do
  IFS=: read lp tend times <<< "$spec"; times=${times//:/ }
  echo "=== $(date '+%F %T') $lp"
  if [ ! -f $W/$lp/done ]; then
    HFILE=~/cfd/h_cfd.json WRITE=$WRITE bash $S/run_case.sh $lp $tend
    rm -rf $W/$lp; mkdir -p $W/$lp; cp -r ~/cfd/$lp/postProcessing $W/$lp/
    grep -q "^[[:space:]]*End$" ~/cfd/$lp/log.run && touch $W/$lp/done || { echo "$lp RUN FAILED"; continue; }
  fi
  tend=$(cd ~/cfd/$lp && ls -d processor0/[0-9]* | xargs -n1 basename | sort -g | tail -1)   # last written
  bash $S/energy_check.sh $lp 0 $tend > $W/$lp/energy_T.txt
  for t in $times; do
    bash $S/slices.sh $lp $t > /dev/null 2>&1
    bash $S/heatpaths.sh $lp $t > /dev/null 2>&1
  done
  bash $S/export3d.sh solid $lp $tend > /dev/null 2>&1
  echo "=== $(date '+%F %T') $lp post done"
done
echo "=== $(date '+%F %T') ALL DONE"

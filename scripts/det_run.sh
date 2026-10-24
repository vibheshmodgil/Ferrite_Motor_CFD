# Detailed-geometry duty point: run + post -> results/detailed/<lp>/   (start inside tmux)
#   bash det_run.sh <lp> <endTime>
# postProcessing, slices at every written time, heatflow + 3D export at the final time, energy balance.
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
lp=$1; C=det_$lp; D=$W/detailed/$lp
echo "=== $(date '+%F %T') $C run"
BASE=~/cfd/base_detailed PREFIX=det_ HFILE=~/cfd/h_cfd_detailed.json bash $S/run_case.sh $lp $2
grep -q "^[[:space:]]*End$" ~/cfd/$C/log.run || { echo "$C RUN FAILED"; exit 1; }
rm -rf $W/$C $D; mkdir -p $D; cp -r ~/cfd/$C/postProcessing $D/
times=$(cd ~/cfd/$C && ls -d processor0/[0-9]* | xargs -n1 basename | grep -vx 0 | sort -g)
tend=$(echo "$times" | tail -1)
echo "=== $(date '+%F %T') post, times: $(echo $times | wc -w), final $tend"
for t in $times; do bash $S/slices.sh $C $t > /dev/null 2>&1; done
bash $S/heatpaths.sh $C $tend > /dev/null 2>&1
bash $S/export3d.sh solid $C $tend > /dev/null 2>&1
bash $S/energy_check.sh $C 0 $tend > $D/energy_T.txt
mv $W/$C/* $D/ && rmdir $W/$C; mv $W/vtk3d/${C}_$tend $D/vtk3d_$tend
touch $D/done; echo "=== $(date '+%F %T') $C done"

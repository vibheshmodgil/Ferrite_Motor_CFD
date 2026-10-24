# One fin variant on the baseline solid model: duty4 to END s -> results/fins/<name>/
#   bash fin_run.sh <name> <base_dir> <h.json> [END=1680]      (start inside tmux; NP=3)
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/fins
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
v=$1; C=fin_${v}_duty4; D=$W/$v; END=${4:-1680}
echo "=== $(date '+%F %T') $C run"
EMISSIVITY=${EMISSIVITY:-0.1} BASE=$2 PREFIX=fin_${v}_ HFILE=$3 NP=3 WRITE=420 bash $S/run_case.sh duty4 $END
grep -q "^[[:space:]]*End$" ~/cfd/$C/log.run || { echo "$C RUN FAILED"; exit 1; }
rm -rf $D; mkdir -p $D; cp -r ~/cfd/$C/postProcessing $D/
tend=$(cd ~/cfd/$C && ls -d processor0/[0-9]* | xargs -n1 basename | sort -g | tail -1)
bash $S/energy_check.sh $C 0 $tend > $D/energy_T.txt
bash $S/heatpaths.sh $C $tend > /dev/null 2>&1; mv /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/$C/heatflow_* $D/ 2>/dev/null
rm -rf /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/$C
python3 $S/energy_balance.py fins/$v duty4
touch $D/done; echo "=== $(date '+%F %T') $C done"

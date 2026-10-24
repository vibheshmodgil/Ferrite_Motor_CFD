# Baseline duty2/3/5, one at a time; end = 1.5x target on the write grid; slices + heatflow at every write.
#   tmux new-session -d -s q3 "bash queue3.sh > ~/cfd/queue3.log 2>&1"
S=$(dirname $(readlink -f $0))
export NP=3   # share the machine with the DETAIL mesh build
WRITE=150 bash $S/duty_runs.sh duty2:1350:$(seq -s: 150 150 1350) > ~/cfd/duty2.log 2>&1
WRITE=300 bash $S/duty_runs.sh duty3:2700:$(seq -s: 300 300 2700) > ~/cfd/duty3.log 2>&1
WRITE=450 bash $S/duty_runs.sh duty5:4050:$(seq -s: 450 450 4050) > ~/cfd/duty5.log 2>&1
echo QUEUE3_DONE

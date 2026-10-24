until grep -q "ALL DONE" ~/cfd/duty2.log; do sleep 5; done
tmux kill-session -t q3; sleep 2; pkill -f "[f]oamMultiRun"; pkill -f "[d]uty_runs"; pkill -f "[m]pirun"
echo "q3 stopped $(date +%T)" > ~/cfd/stopq3.log

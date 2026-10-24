# wait until e2 tmux ends, then balance summary + per-region rates
while tmux has-session -t e2 2>/dev/null; do sleep 10; done
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/_s.sh 2>&1 | sed -n 1,4p; python3 /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/_r.py

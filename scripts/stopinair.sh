tmux kill-session -t inair 2>/dev/null
for p in $(pgrep -f inair_cfd.sh); do kill $p; done
for p in $(pgrep -f "foamRun -parallel"); do kill $p; done
sleep 2; pgrep -fa "foamRun|inair_cfd" | grep -v pgrep || echo clear

date; uptime -p; tmux ls 2>&1
grep -E "^===|== |STOP|FAILED" ~/cfd/pipeline.log | tail -8
for c in continuous peak_power cruise max_speed; do
  L=~/cfd/$c/log.run; [ -f $L ] || continue
  n=$(grep -c "^Time =" $L); e=$(grep -c FATAL $L)
  w=$(tail -1 ~/cfd/$c/postProcessing/winding/T_winding/0/volFieldValue.dat 2>/dev/null | awk '{printf "%.0f s, winding max %.1f C", $1, $2-273.15}')
  echo "$c: $n steps, fatal=$e, $w"
done
free -g | sed -n 2p

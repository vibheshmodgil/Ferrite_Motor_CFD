# progress of ~/cfd/u666_e2: sim time, wall, T max per region, errors
C=~/cfd/u666_e2; cd $C
echo "time $(grep '^Time = ' log.run | tail -1) wall $(( $(date +%s) - $(cat t_start) ))s $(tmux has-session -t e2 2>/dev/null && echo running || echo stopped)"
grep -m3 -iE "fatal|nan|error" log.run | cut -c1-160
for f in postProcessing/*/T_*/0/*.dat; do echo -n "$(echo $f | cut -d/ -f3)=$(tail -1 $f | awk '{printf "%.1f", $2}') "; done; echo

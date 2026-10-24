cd /home/cfd/cfd/inair_continuous; ls; ls processor0
f=log.run; wc -l < $f; grep -c '^Time =' $f; grep 'Time =' $f | tail -1; grep 'continuity' $f | tail -1
grep 'Solving for p_rgh' $f | tail -1 | cut -c1-100; grep -i 'converged\|End' $f | tail -2
ls $(ls -d [0-9]* | sort -n | tail -1)

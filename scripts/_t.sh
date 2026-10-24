cd ~/cfd/u666_etest/postProcessing
for r in *; do for f in $r/T_*/0/*.dat; do echo "$f $(tail -1 $f)"; done; done 2>/dev/null | cut -c1-110

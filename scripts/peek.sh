cd ~/cfd/$1
grep "Solving for e" log.run | tail -16 | awk '{print $1, $NF}' | tr '\n' ' '; echo
grep ExecutionTime log.run | tail -1
for r in winding magnets housing stator rotor; do echo "$r $(tail -1 postProcessing/$r/T_$r/0/volFieldValue.dat)"; done

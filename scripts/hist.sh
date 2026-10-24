cd ~/cfd/$1/postProcessing
for r in winding stator inair housing rotor magnets shaft bearings; do
  echo "$r: $(sed -n 5,12p $r/T_$r/0/volFieldValue.dat | awk '{printf "%.4g ", $2}')"
done

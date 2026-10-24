cd ~/cfd/base_solids/constant
for r in bearings housing inair magnets rotor shaft stator winding; do
  echo "$r $(head -c 3000 $r/polyMesh/owner | tr -d '\0' | grep -ao 'nCells:[ ]*[0-9]*')"
done

source /opt/openfoam12/etc/bashrc 2>/dev/null || true
C=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD
B=~/cfd/u666_base_nc
bash $C/scripts/u666_assemble_nc.sh $B > $C/mesh/u666/assemble_nc.log 2>&1 || { echo ASSEMBLE FAILED; tail $C/mesh/u666/assemble_nc.log; exit 1; }
cd $B
for r in $(ls constant); do
  checkMesh -region $r > log.check.$r 2>&1
  echo "$r cells $(grep -m1 '^\s*cells:' log.check.$r | awk '{print $2}') $(grep -E 'Mesh OK|Failed [0-9]+ mesh' log.check.$r) $(grep -E 'Max non-orth|Max skewness' log.check.$r | tr -s ' ' | tr '\n' ' ')"
done
python3 $C/scripts/u666_iface_area.py $B

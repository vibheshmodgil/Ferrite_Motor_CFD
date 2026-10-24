# Post-process the internal-air CFD: bash inair_post.sh [thermal_case=continuous] -> results/inair_<case>
#   wall_q.txt : surface  T_wall[K]  Q[W]  area[m2]   (+ "air <mean T>")    h = Q / (area (T_wall - T_air))
#   inair_{z,x}.vtk : U and T on a radial plane in the drive-end space (z = -40 mm) and the axial mid-plane
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
N=inair_${1:-continuous}; C=~/cfd/$N; cd $C; W=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/$N; mkdir -p $W
LT=$(foamListTimes -latestTime | tail -1)
rm -rf postProcessing/wallHeatFlux postProcessing/airT
foamPostProcess -solver fluid -func wallHeatFlux -time $LT > log.post_whf 2>&1
foamPostProcess -solver fluid -func "volFieldValue(fields=(T), operation=volAverage)" -time $LT > log.post_air 2>&1
AIR=$(python3 -c "
import re, numpy as np
t = open('$LT/T').read(); i = t.index('internalField'); n = int(re.search(r'List<scalar>\s*(\d+)', t[i:]).group(1))
s = t[i:].split('(', 1)[1]; print(round(float(np.array(s[:s.index(chr(10)+')')].split(), float)[:n].mean()), 2))")
f=$(find postProcessing/wallHeatFlux -name wallHeatFlux.dat | head -1)
: > $W/wall_q.txt
for r in winding stator housing rotor shaft bearings; do
  p=inair_to_$r
  tw=$(grep -oE "$p \{ type fixedValue; value uniform [0-9.]+" 0/T | awk '{print $NF}')
  q=$(grep -v '^#' $f | awk -v p=$p '$2==p {print $5}' | tail -1)
  a=$(foamPostProcess -func "patchIntegrate(patch=$p, fields=(T))" -time $LT 2>/dev/null | grep -oE "of T = [0-9.e+-]+" | awk -v t=$tw '{print $NF/t}')
  echo "$r $tw $q $a" >> $W/wall_q.txt
done
echo "air $AIR" >> $W/wall_q.txt
for ax in z x; do
  n=$([ $ax = z ] && echo "(0 0 1)" || echo "(1 0 0)"); pt=$([ $ax = z ] && echo "(0 0 -0.040)" || echo "(0 0 0)")
  rm -rf postProcessing/cutPlaneSurface*
  foamPostProcess -solver fluid -func "cutPlaneSurface(point=$pt, normal=$n, U, T)" -time $LT > /dev/null 2>&1
  v=$(find postProcessing -path "*cutPlaneSurface*" -name "*.vtk" | head -1); [ -n "$v" ] && cp "$v" $W/inair_$ax.vtk
done
cat $W/wall_q.txt

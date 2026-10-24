# Global energy balance of a finished thermal case between two written times:
#   bash energy_check.sh <case> <t1> <t2>   -> per region volume integral of T (K m3) at both times
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
cd ~/cfd/$1 || exit 1
for t in $2 $3; do [ -d $t ] || reconstructPar -allRegions -time $t > /dev/null 2>&1; done
for r in $(ls -d constant/*/polyMesh | cut -d/ -f2); do
  rm -rf postProcessing/$r/volIntegrate*
  foamPostProcess -region $r -func "volIntegrate(T)" -time "$2,$3" > log.vi_$r 2>&1
  f=$(find postProcessing/$r -path "*volIntegrate*" -name "*.dat" | head -1)
  echo "$r $(grep -v '^#' $f | awk '{printf "%s %s ", $1, $2}')"
done

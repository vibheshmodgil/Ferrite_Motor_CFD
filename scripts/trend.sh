f=~/cfd/$1/postProcessing/winding/T_winding/0/volFieldValue.dat
awk 'NR>4 && ($1 % 1800 == 0) {printf "%6.0f s  %6.1f C\n", $1, $2-273.15}' $f
grep -c "^End" ~/cfd/$1/log.run; tail -3 ~/cfd/$1/log.run | head -2

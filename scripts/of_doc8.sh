d=/opt/openfoam12/tutorials/fluid/angledDuctLTS
sed '1,/^}/d' $d/system/fvSolution | grep -v '^\s*$' | sed -n '/PIMPLE/,$p'
grep -A3 ddtSchemes $d/system/fvSchemes

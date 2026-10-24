source /opt/openfoam12/etc/bashrc
S=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts
ADIABATIC=1 JOULE_TC=0 python3 $S/u666_make_case.py ~/cfd/u666_base_nc ~/cfd/u666_etest etest --lp-file $S/../u666_loadpoints.json
cd ~/cfd/u666_etest
sed -i 's/^endTime .*/endTime 10;/; s/^writeInterval .*/writeInterval 10;/' system/controlDict
sed -i "s/nOuterCorrectors [0-9]*/nOuterCorrectors 4/" system/fvSolution
decomposePar -allRegions > log.decompose 2>&1
bash $S/_r11.sh

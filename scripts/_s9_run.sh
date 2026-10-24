D=/mnt/c/Users/vibhe/Downloads/OUTPUT/CFD
export MAXCO=${MAXCO:-3} MDT=${MDT:-0.1} WI=${WI:-100}; cd ~; bash $D/scripts/u666_air_case.sh $D/mesh/u666/air_hxt.msh ${TW:-343.15} > ~/s9_run.log 2>&1; echo EXIT >> ~/s9_run.log

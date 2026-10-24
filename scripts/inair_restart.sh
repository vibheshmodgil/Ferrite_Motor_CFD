# Continue the internal-air CFD from its last good state (iteration 500) with conservative settings, then post-process
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
C=~/cfd/inair_continuous; cd $C
sed -i 's/relaxationFactors.*/relaxationFactors { fields { rho 1; p_rgh 0.2; } equations { U 0.3; h 0.4; k 0.3; omega 0.3; } }/' system/fvSolution
sed -i 's/nNonOrthogonalCorrectors 1;/nNonOrthogonalCorrectors 2;/' system/fvSolution
sed -i 's/div(phi,U) bounded Gauss linearUpwind limited;/div(phi,U) bounded Gauss upwind;/' system/fvSchemes
grep -q "endTime 2000" system/controlDict || sed -i "s/startFrom startTime;/startFrom latestTime;/; s/endTime 2500;/endTime 2000;/" system/controlDict
for p in processor*; do (cd $p; ls | grep -E '^[0-9]+$' | awk '$1>500' | xargs -r rm -rf); done
mpirun -np 4 foamRun -parallel > log.run2 2>&1
reconstructPar -latestTime > log.reconstruct2 2>&1
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/inair_post.sh
echo INAIR_DONE

# motor skin with the CFD wall heat flux -> results/air/motor_skin.vtk
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
cd ~/cfd/air; rm -rf postProcessing/skin
cat > system/skinDict <<D
FoamFile { format ascii; class dictionary; object skinDict; }
heat { type wallHeatFlux; libs ("libfieldFunctionObjects.so"); patches (motor); }
    skin
    {
        type surfaces; libs ("libsampling.so"); surfaceFormat vtk; interpolationScheme cellPoint;
        fields (wallHeatFlux);
        surfaces ( motor { type patch; patches (motor); interpolate false; } );
    }
D
foamPostProcess -solver fluid -dict system/skinDict -time 3000 > log.skin 2>&1
grep -iE "FATAL|cannot" -A3 log.skin | head -6
f=$(find postProcessing/skin -name "*.vtk" | head -1); echo "$f"
[ -n "$f" ] && cp "$f" /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/air/motor_skin.vtk && grep -a -c wallHeatFlux /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/results/air/motor_skin.vtk

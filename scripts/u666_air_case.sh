# U666 external natural-convection CFD (copy of air_case.sh): steady, laminar, buoyant air around the motor skin.
# Motor skin held at T_WALL; box faces open to 40 C ambient. Output: wallHeatFlux -> h per face (map_h.py).
#   bash air_case.sh <air.msh> [T_wall_K]
set -e
source /opt/openfoam12/etc/bashrc 2>/dev/null || true
S=$(dirname $(readlink -f $0)); MSH=$(readlink -f $1); TW=${2:-373.15}; TA=313.15; C=${AIRC:-~/cfd/u666_air}   # AIRC: another case dir (fin variants)
rm -rf $C; mkdir -p $C/system $C/constant $C/0; cd $C
H='FoamFile { format ascii; class dictionary; object x; }'
cat > system/controlDict <<EOF
$H
application foamRun; solver fluid;
startFrom latestTime; startTime 0; stopAt endTime; endTime 3000; deltaT 1;
writeControl timeStep; writeInterval ${WI:-100}; purgeWrite 3; writeFormat ascii; timeFormat general;
runTimeModifiable yes;
functions
{
    heat { type wallHeatFlux; libs ("libfieldFunctionObjects.so"); patches (motor); writeControl writeTime; }
}
EOF
cat > system/fvSchemes <<EOF
$H
ddtSchemes { default localEuler; }     // pseudo-transient (local time step): steadyState SIMPLE diverged on the fin mesh (KNOWN_ISSUES 12)
gradSchemes { default Gauss linear; limited cellLimited Gauss linear 1; grad(U) \$limited; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss upwind;
    div(phi,h) bounded Gauss upwind;
    div(phi,K) bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.33; }
interpolationSchemes { default linear; }
snGradSchemes { default limited corrected 0.33; }
EOF
cat > system/fvSolution <<EOF
$H
solvers
{
    p_rgh { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }
    "(U|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-6; relTol 0.1; }
    "rho.*" { solver diagonal; }
    p_rghFinal { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0; }
    "(U|h)Final" { solver PBiCGStab; preconditioner DILU; tolerance 1e-6; relTol 0; }
}
PIMPLE
{
    momentumPredictor yes; nOuterCorrectors 1; nCorrectors 2;
    maxCo ${MAXCO:-2}; rDeltaTSmoothingCoeff 0.1; rDeltaTDampingCoeff 1; maxDeltaT ${MDT:-0.1}; rDeltaTMax 1e3;
    nNonOrthogonalCorrectors 2;
    pRefCell 0;
    pRefValue 0;
    residualControl { p_rgh 1e-4; U 1e-4; h 1e-5; }
}
relaxationFactors { fields { rho 1; } equations { ".*" 1; } }
EOF
cat > system/decomposeParDict <<EOF
$H
numberOfSubdomains 4; method scotch;
EOF
cat > constant/physicalProperties <<EOF
$H
thermoType
{
    type heRhoThermo; mixture pureMixture; transport const; thermo hConst;
    equationOfState perfectGas; specie specie; energy sensibleEnthalpy;
}
mixture
{
    specie { molWeight 28.96; }
    thermodynamics { Cp 1007; hf 0; }
    transport { mu 1.95e-05; Pr 0.71; }
}
EOF
cat > constant/fvConstraints <<EOF
$H
limitT { type limitTemperature; select all; min 300; max $(awk "BEGIN{print $TW+2}"); }   // guard: 16 sliver cells (z~97, quality 0.03) gave T<0
EOF
cat > constant/momentumTransport <<EOF
$H
simulationType laminar;     // Ra ~ 5e7 on the 188 mm fin diameter: laminar natural convection
EOF
cat > constant/g <<EOF
$H
dimensions [0 1 -2 0 0 0 0]; value (0 -9.81 0);     // shaft horizontal (z), y up
EOF
cat > constant/pRef <<EOF
$H
dimensions [1 -1 -2 0 0 0 0]; value 1e5;
EOF
cat > 0/T <<EOF
FoamFile { format ascii; class volScalarField; object T; }
dimensions [0 0 0 1 0 0 0]; internalField uniform $TA;
boundaryField
{
    ambient { type fixedValue; value uniform $TA; }      // closed box, walls at ambient: still room air
    motor   { type fixedValue; value uniform $TW; }
}
EOF
cat > 0/U <<EOF
FoamFile { format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField
{
    ambient { type noSlip; }
    motor   { type noSlip; }
}
EOF
cat > 0/p_rgh <<EOF
FoamFile { format ascii; class volScalarField; object p_rgh; }
dimensions [1 -1 -2 0 0 0 0]; internalField uniform 0;
boundaryField
{
    ambient { type fixedFluxPressure; value uniform 0; }   // S9: closed box again (open box: whole domain fell at ~9 m/s; p_rgh=0 walls blew up)
    motor   { type fixedFluxPressure; value uniform 0; }
}
EOF
cat > 0/p <<EOF
FoamFile { format ascii; class volScalarField; object p; }
dimensions [1 -1 -2 0 0 0 0]; internalField uniform 1e5;
boundaryField { ".*" { type calculated; value uniform 1e5; } }
EOF
gmshToFoam $MSH > log.gmshToFoam 2>&1
transformPoints "scale=(1e-3 1e-3 1e-3)" > log.transform 2>&1
foamDictionary constant/polyMesh/boundary -entry entry0/motor/type -set wall > /dev/null
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Max non-orth|Mesh OK|Failed" log.checkMesh
decomposePar > log.decompose 2>&1
set +e
# run in chunks with the aircheck gate between them (KNOWN_ISSUES #12): stop as soon as U max > 5 m/s
for E in 300 600 1000 1500 2000 2500 3000; do
  foamDictionary system/controlDict -entry endTime -set $E > /dev/null
  mpirun -np ${NP:-4} foamRun -parallel >> log.run 2>&1 || true
  reconstructPar -latestTime > log.reconstruct 2>&1
  tail -2 log.run | head -1
  bash $S/u666_aircheck.sh > log.aircheck_$E 2>&1; tail -1 log.aircheck_$E
  python3 - <<PY || { echo "AIRCHECK FAILED at $E: U max > 5 m/s, non-physical; stopped"; exit 2; }
import re,sys; m=re.search(r"U max ([0-9.eE+-]+)", open("log.aircheck_$E").read()); sys.exit(0 if m and float(m.group(1)) <= 5.0 else 1)
PY
  grep -q "solution converged" log.run && break
done
bash $S/u666_aircheck.sh || { echo "AIRCHECK FAILED (p99 > 0.8 m/s): do not map h"; exit 2; }

cd ~/cfd/air
sed -i 's/tolerance 1e-8; relTol 0.1;/tolerance 1e-6; relTol 0.1;/; s/tolerance 1e-8; relTol 0;/tolerance 1e-6; relTol 0;/; s/nNonOrthogonalCorrectors 1;/nNonOrthogonalCorrectors 0;/; s/tolerance 1e-7; relTol 0.01;/tolerance 1e-6; relTol 0.05;/' system/fvSolution
sed -i 's/endTime 1500;/endTime 1000;/' system/controlDict
grep -E "tolerance|nNonOrth" system/fvSolution; grep -o "endTime [0-9]*" system/controlDict

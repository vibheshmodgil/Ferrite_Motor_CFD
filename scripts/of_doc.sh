source /opt/openfoam12/etc/bashrc 2>/dev/null
S=$FOAM_SRC
doc(){ awk '/^Description/,/^SourceFiles/' "$1" | grep -v '^SourceFiles' | head -${2:-80}; echo =========; }
doc $S/fvModels/general/heatSource/heatSource.H 40
doc $S/ThermophysicalTransportModels/coupledThermophysicalTransportModels/coupledTemperature/coupledTemperatureFvPatchScalarField.H 70
doc $S/ThermophysicalTransportModels/coupledThermophysicalTransportModels/externalTemperature/externalTemperatureFvPatchScalarField.H 90
doc $S/ThermophysicalTransportModels/solid/anisotropic/anisotropic.H 70

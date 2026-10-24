# builds libcoupledTemperatureNC: coupledTemperature copy whose uncovered nc-interface faces (sumKappaByDelta=0) go adiabatic
source /opt/openfoam12/etc/bashrc
D=/opt/openfoam12/src/ThermophysicalTransportModels/coupledThermophysicalTransportModels/coupledTemperature
B=$HOME/cfd/ctnc; rm -rf $B; mkdir -p $B/Make; cd $B
for e in C H; do sed 's/coupledTemperature/coupledTemperatureNC/g' $D/coupledTemperatureFvPatchScalarField.$e > coupledTemperatureNCFvPatchScalarField.$e; done
python3 - <<'PY'
f="coupledTemperatureNCFvPatchScalarField.C"; s=open(f).read()
old="""    this->valueFraction() =
        sumKappaByDelta()/(kappa()*patch().deltaCoeffs() + sumKappaByDelta());

    this->refValue() = (sumKappaTByDelta() + sumq)/sumKappaByDelta();
"""
new="""    // ponytail: faces with no neighbour coverage (non-conformal) -> adiabatic
    const scalarField kd(kappa()*patch().deltaCoeffs());
    scalarField& skd = const_cast<scalarField&>(sumKappaByDelta());
    scalarField& sktd = const_cast<scalarField&>(sumKappaTByDelta());
    forAll(skd, i)
    {
        if (!(skd[i] >= 1e-9*kd[i]) || !(mag(sktd[i]) < great)) { skd[i] = 0; sktd[i] = 0; }
    }
    if (getenv("NCDBG")) { label a=0,b=0,c=0,d=0,e=0; forAll(skd,i){ a+=!std::isfinite(kd[i]); b+=!std::isfinite(skd[i]); c+=!std::isfinite(sktd[i]); d+=!std::isfinite(sumq[i]); e+=!std::isfinite(qByKappa()[i]); } Pout<< "NCDBG " << patch().name() << " kd,skd,sktd,sumq,qbk nan: " << a << b << c << d << e << endl; }
    this->valueFraction() = skd/(kd + skd);
    this->refValue() = (sktd + sumq)/max(skd, small);
"""
s = s.replace(old,new)
m="    mixedFvPatchScalarField::updateCoeffs();"
assert m in s
s = s.replace(m, '    if (getenv("NCDBG2")) { Pout<< "NCDBG2 " << patch().name() << " ref " << min(this->refValue()) << " " << max(this->refValue()) << " vf " << min(this->valueFraction()) << " " << max(this->valueFraction()) << " kd " << min(kd) << " " << max(kd) << " skd " << min(skd) << " " << max(skd) << endl; }'+chr(10) + m, 1)
open(f,"w").write(s)
PY
echo 'coupledTemperatureNCFvPatchScalarField.C
LIB = $(FOAM_USER_LIBBIN)/libcoupledTemperatureNC' > Make/files
cat > Make/options <<'OP'
EXE_INC = \
    -I$(LIB_SRC)/ThermophysicalTransportModels/thermophysicalTransportModel/lnInclude \
    -I$(LIB_SRC)/ThermophysicalTransportModels/coupledThermophysicalTransportModels/lnInclude \
    -I$(LIB_SRC)/finiteVolume/lnInclude \
    -I$(LIB_SRC)/meshTools/lnInclude
LIB_LIBS = -lthermophysicalTransportModel -lcoupledThermophysicalTransportModels -lfiniteVolume -lmeshTools
OP
wmake libso 2>&1 | tail -15

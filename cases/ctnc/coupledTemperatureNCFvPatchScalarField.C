/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Copyright (C) 2011-2024 OpenFOAM Foundation
     \\/     M anipulation  |
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

\*---------------------------------------------------------------------------*/

#include "coupledTemperatureNCFvPatchScalarField.H"
#include "thermophysicalTransportModel.H"
#include "volFields.H"
#include "fieldMapper.H"
#include "mappedFvPatchBaseBase.H"
#include "addToRunTimeSelectionTable.H"

// * * * * * * * * * * * * * Protected Member Functions  * * * * * * * * * * //

void Foam::coupledTemperatureNCFvPatchScalarField::getThis
(
    tmp<scalarField>& kappa,
    tmp<scalarField>& sumKappaTByDelta,
    tmp<scalarField>& sumKappaByDeltaNbr,
    scalarField& sumq,
    tmp<scalarField>& qByKappa
) const
{
    const thermophysicalTransportModel& ttm =
        patch().boundaryMesh().mesh()
       .lookupType<thermophysicalTransportModel>();

    kappa = ttm.kappaEff(patch().index());

    qByKappa = sumq/kappa();

    sumq = 0;

    tmp<scalarField> qCorr(ttm.qCorr(patch().index()));

    if (qCorr.valid())
    {
        sumq += qCorr;
    }
}


void Foam::coupledTemperatureNCFvPatchScalarField::getNbr
(
    tmp<scalarField>& sumKappaTByDeltaNbr,
    tmp<scalarField>& sumKappaByDeltaNbr,
    tmp<scalarField>& qNbr
) const
{
    const thermophysicalTransportModel& ttm =
        patch().boundaryMesh().mesh()
       .lookupType<thermophysicalTransportModel>();

    sumKappaByDeltaNbr = ttm.kappaEff(patch().index())*patch().deltaCoeffs();

    sumKappaTByDeltaNbr = sumKappaByDeltaNbr()*patchInternalField();

    qNbr = ttm.qCorr(patch().index());
}


void Foam::coupledTemperatureNCFvPatchScalarField::getNbr
(
    tmp<scalarField>& TrefNbr,
    tmp<scalarField>& qNbr
) const
{
    const thermophysicalTransportModel& ttm =
        patch().boundaryMesh().mesh()
       .lookupType<thermophysicalTransportModel>();

    const fvPatchScalarField& Tp =
        patch().lookupPatchField<volScalarField, scalar>
        (
            internalField().name()
        );

    TrefNbr = Tp;

    qNbr = ttm.qCorr(patch().index());
}


void Foam::coupledTemperatureNCFvPatchScalarField::add
(
    tmp<scalarField>& result,
    const tmp<scalarField>& field
) const
{
    if (result.valid())
    {
        result.ref() += field;
    }
    else
    {
        if (field.isTmp())
        {
            result = field;
        }
        else
        {
            result = field().clone();
        }
    }
}


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::coupledTemperatureNCFvPatchScalarField::
coupledTemperatureNCFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const dictionary& dict
)
:
    mixedFvPatchScalarField(p, iF, dict, false),
    TnbrName_(dict.lookupOrDefault<word>("Tnbr", "T")),
    qrNbrName_(dict.lookupOrDefault<word>("qrNbr", "none")),
    qrName_(dict.lookupOrDefault<word>("qr", "none")),
    thicknessLayers_(0),
    kappaLayers_(0),
    qs_(),
    Qs_(0),
    wallKappaByDelta_(0)
{
    mappedPatchBaseBase::validateMapForField
    (
        *this,
        iF,
        dict,
        mappedPatchBaseBase::from::differentPatch
    );

    if (dict.found("thicknessLayers"))
    {
        dict.lookup("thicknessLayers") >> thicknessLayers_;
        dict.lookup("kappaLayers") >> kappaLayers_;

        if (thicknessLayers_.size() > 0)
        {
            // Calculate effective thermal resistance by harmonic averaging
            forAll(thicknessLayers_, i)
            {
                wallKappaByDelta_ += thicknessLayers_[i]/kappaLayers_[i];
            }
            wallKappaByDelta_ = 1/wallKappaByDelta_;
        }
    }

    if (dict.found("qs"))
    {
        if (dict.found("Qs"))
        {
            FatalIOErrorInFunction(dict)
                << "Either qs or Qs should be specified, not both"
                << exit(FatalIOError);
        }

        qs_ = new scalarField("qs", dimPower/dimTime, dict, p.size());
    }
    else if (dict.found("Qs"))
    {
        Qs_ = dict.lookup<scalar>("Qs");
        qs_ = new scalarField(p.size(), Qs_/gSum(patch().magSf()));
    }

    fvPatchScalarField::operator=
    (
        scalarField("value", iF.dimensions(), dict, p.size())
    );

    if (dict.found("refValue"))
    {
        // Full restart
        refValue() = scalarField("refValue", iF.dimensions(), dict, p.size());
        refGrad() =
            scalarField
            (
                "refGradient",
                iF.dimensions()/dimLength,
                dict,
                p.size()
            );
        valueFraction() =
            scalarField("valueFraction", unitFraction, dict, p.size());
    }
    else
    {
        // Start from user entered data. Assume fixedValue.
        refValue() = *this;
        refGrad() = 0;
        valueFraction() = 1;
    }
}


Foam::coupledTemperatureNCFvPatchScalarField::
coupledTemperatureNCFvPatchScalarField
(
    const coupledTemperatureNCFvPatchScalarField& psf,
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const fieldMapper& mapper
)
:
    mixedFvPatchScalarField(psf, p, iF, mapper),
    TnbrName_(psf.TnbrName_),
    qrNbrName_(psf.qrNbrName_),
    qrName_(psf.qrName_),
    thicknessLayers_(psf.thicknessLayers_),
    kappaLayers_(psf.kappaLayers_),
    qs_(psf.qs_.valid() ? new scalarField(p.size()) : nullptr),
    Qs_(psf.Qs_),
    wallKappaByDelta_(psf.wallKappaByDelta_)
{
    map(psf, mapper);
}


Foam::coupledTemperatureNCFvPatchScalarField::
coupledTemperatureNCFvPatchScalarField
(
    const coupledTemperatureNCFvPatchScalarField& psf,
    const DimensionedField<scalar, volMesh>& iF
)
:
    mixedFvPatchScalarField(psf, iF),
    TnbrName_(psf.TnbrName_),
    qrNbrName_(psf.qrNbrName_),
    qrName_(psf.qrName_),
    thicknessLayers_(psf.thicknessLayers_),
    kappaLayers_(psf.kappaLayers_),
    qs_(psf.qs_, false),
    Qs_(psf.Qs_),
    wallKappaByDelta_(psf.wallKappaByDelta_)
{}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void Foam::coupledTemperatureNCFvPatchScalarField::map
(
    const coupledTemperatureNCFvPatchScalarField& ptf,
    const fieldMapper& mapper
)
{
    // Unmapped faces are considered zero-gradient/adiabatic
    mapper(*this, ptf, [&](){ return patchInternalField(); });
    mapper(refValue(), ptf.refValue(), [&](){ return patchInternalField(); });
    mapper(refGrad(), ptf.refGrad(), scalar(0));
    mapper(valueFraction(), ptf.valueFraction(), scalar(0));

    // Map the heat flux, if present
    if (ptf.qs_.valid())
    {
        mapper(qs_(), ptf.qs_());
    }
}


void Foam::coupledTemperatureNCFvPatchScalarField::map
(
    const fvPatchScalarField& ptf,
    const fieldMapper& mapper
)
{
    map(refCast<const coupledTemperatureNCFvPatchScalarField>(ptf), mapper);
}


void Foam::coupledTemperatureNCFvPatchScalarField::reset
(
    const fvPatchScalarField& ptf
)
{
    mixedFvPatchScalarField::reset(ptf);

    const coupledTemperatureNCFvPatchScalarField& tiptf =
        refCast<const coupledTemperatureNCFvPatchScalarField>(ptf);

    if (tiptf.qs_.valid())
    {
        qs_().reset(tiptf.qs_());
    }
}


void Foam::coupledTemperatureNCFvPatchScalarField::updateCoeffs()
{
    if (updated())
    {
        return;
    }

    // Since we're inside initEvaluate/evaluate there might be processor
    // comms underway. Change the tag we use.
    int oldTag = UPstream::msgType();
    UPstream::msgType() = oldTag + 1;

    // Get the mapper and the neighbouring patch
    const mappedFvPatchBaseBase& mapper =
        mappedFvPatchBaseBase::getMap(patch());
    const fvPatch& patchNbr = mapper.nbrFvPatch();

    const fvPatchScalarField& TpNbr =
        patchNbr.lookupPatchField<volScalarField, scalar>(TnbrName_);

    if (!isA<coupledTemperatureNCFvPatchScalarField>(TpNbr))
    {
        FatalErrorInFunction
            << "Patch field for " << internalField().name() << " on "
            << this->patch().name() << " is of type "
            << coupledTemperatureNCFvPatchScalarField::typeName
            << endl << "The neighbouring patch field "
            << internalField().name() << " on "
            << patchNbr.name() << " is required to be the same, but is "
            << "currently of type " << TpNbr.type() << exit(FatalError);
    }

    const coupledTemperatureNCFvPatchScalarField& coupledTemperatureNCNbr =
        refCast<const coupledTemperatureNCFvPatchScalarField>(TpNbr);

    scalarField sumq(size(), 0);

    if (qs_.valid())
    {
        sumq += qs_();
    }

    if (qrName_ != "none")
    {
        sumq += patch().lookupPatchField<volScalarField, scalar>(qrName_);
    }

    if (qrNbrName_ != "none")
    {
        sumq += mapper.fromNeighbour
        (
            patchNbr.lookupPatchField<volScalarField, scalar>(qrNbrName_)
        );
    }

    tmp<scalarField> kappa;
    tmp<scalarField> sumKappaTByDelta;
    tmp<scalarField> sumKappaByDelta;
    tmp<scalarField> qByKappa;

    // q = alpha.this*sumq
    getThis(kappa, sumKappaTByDelta, sumKappaByDelta, sumq, qByKappa);

    // Add neighbour contributions
    {
        tmp<scalarField> sumKappaTByDeltaNbr;
        tmp<scalarField> sumKappaByDeltaNbr;
        tmp<scalarField> qNbr;

        if (wallKappaByDelta_ == 0)
        {
            coupledTemperatureNCNbr.getNbr
            (
                sumKappaTByDeltaNbr,
                sumKappaByDeltaNbr,
                qNbr
            );

            add(sumKappaTByDelta, mapper.fromNeighbour(sumKappaTByDeltaNbr));
            add(sumKappaByDelta, mapper.fromNeighbour(sumKappaByDeltaNbr));
        }
        else
        {
            // Get the neighbour wall temperature and flux correction
            tmp<scalarField> TwNbr;
            coupledTemperatureNCNbr.getNbr(TwNbr, qNbr);

            add(sumKappaByDelta, scalarField(size(), wallKappaByDelta_));
            add
            (
                sumKappaTByDelta,
                wallKappaByDelta_*mapper.fromNeighbour(TwNbr)
            );
        }

        if (qNbr.valid())
        {
            sumq += mapper.fromNeighbour(qNbr);
        }
    }

    // ponytail: faces with no neighbour coverage (non-conformal) -> adiabatic
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

    this->refGrad() = qByKappa;

    if (getenv("NCDBG2")) { Pout<< "NCDBG2 " << patch().name() << " ref " << min(this->refValue()) << " " << max(this->refValue()) << " vf " << min(this->valueFraction()) << " " << max(this->valueFraction()) << " kd " << min(kd) << " " << max(kd) << " skd " << min(skd) << " " << max(skd) << endl; }
    mixedFvPatchScalarField::updateCoeffs();

    if (debug)
    {
        const scalar Q = gSum(kappa()*patch().magSf()*snGrad());

        Info<< patch().boundaryMesh().mesh().name() << ':'
            << patch().name() << ':'
            << this->internalField().name() << " <- "
            << mapper.nbrMesh().name() << ':'
            << patchNbr.name() << ':'
            << this->internalField().name() << " :"
            << " heat transfer rate:" << Q
            << " walltemperature "
            << " min:" << gMin(*this)
            << " max:" << gMax(*this)
            << " avg:" << gAverage(*this)
            << endl;
    }

    // Restore tag
    UPstream::msgType() = oldTag;
}


void Foam::coupledTemperatureNCFvPatchScalarField::write
(
    Ostream& os
) const
{
    mixedFvPatchScalarField::write(os);

    writeEntryIfDifferent<word>(os, "Tnbr", "T", TnbrName_);
    writeEntryIfDifferent<word>(os, "qrNbr", "none", qrNbrName_);
    writeEntryIfDifferent<word>(os, "qr", "none", qrName_);

    if (Qs_ != 0)
    {
        writeEntry(os, "Qs", Qs_);
    }
    else if (qs_.valid())
    {
        writeEntry(os, "qs", qs_());
    }

    if (thicknessLayers_.size())
    {
        writeEntry(os, "thicknessLayers", thicknessLayers_);
        writeEntry(os, "kappaLayers", kappaLayers_);
    }
}


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
    makePatchTypeField
    (
        fvPatchScalarField,
        coupledTemperatureNCFvPatchScalarField
    );

    addBackwardCompatibleToRunTimeSelectionTable
    (
        fvPatchScalarField,
        coupledTemperatureNCFvPatchScalarField,
        patchMapper,
        turbulentTemperatureCoupledBaffleMixed,
        "compressible::turbulentTemperatureCoupledBaffleMixed"
    );

    addBackwardCompatibleToRunTimeSelectionTable
    (
        fvPatchScalarField,
        coupledTemperatureNCFvPatchScalarField,
        dictionary,
        turbulentTemperatureCoupledBaffleMixed,
        "compressible::turbulentTemperatureCoupledBaffleMixed"
    );


    addBackwardCompatibleToRunTimeSelectionTable
    (
        fvPatchScalarField,
        coupledTemperatureNCFvPatchScalarField,
        patchMapper,
        turbulentTemperatureRadCoupledMixed,
        "compressible::turbulentTemperatureRadCoupledMixed"
    );

    addBackwardCompatibleToRunTimeSelectionTable
    (
        fvPatchScalarField,
        coupledTemperatureNCFvPatchScalarField,
        dictionary,
        turbulentTemperatureRadCoupledMixed,
        "compressible::turbulentTemperatureRadCoupledMixed"
    );
}


// ************************************************************************* //

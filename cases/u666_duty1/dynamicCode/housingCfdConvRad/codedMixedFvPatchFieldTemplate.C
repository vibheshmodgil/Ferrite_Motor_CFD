/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Copyright (C) YEAR OpenFOAM Foundation
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

#include "codedMixedFvPatchFieldTemplate.H"
#include "addToRunTimeSelectionTable.H"
#include "fieldMapper.H"
#include "volFields.H"
#include "surfaceFields.H"
#include "read.H"

//{{{ begin codeInclude

//}}} end codeInclude


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

// * * * * * * * * * * * * * * * Local Functions * * * * * * * * * * * * * * //

//{{{ begin localCode

//}}} end localCode


// * * * * * * * * * * * * * * * Global Functions  * * * * * * * * * * * * * //

extern "C"
{
    // dynamicCode:
    // SHA1 = 801610e9e92f990850ea4e7040613fe45fc3c7c9
    //
    // unique function name that can be checked if the correct library version
    // has been loaded
    void housingCfdConvRad_801610e9e92f990850ea4e7040613fe45fc3c7c9(bool load)
    {
        if (load)
        {
            // code that can be explicitly executed after loading
        }
        else
        {
            // code that can be explicitly executed before unloading
        }
    }
}

// * * * * * * * * * * * * * * Static Data Members * * * * * * * * * * * * * //

makeRemovablePatchTypeField
(
    fvPatchScalarField,
    housingCfdConvRadMixedValueFvPatchScalarField
);


const char* const housingCfdConvRadMixedValueFvPatchScalarField::SHA1sum =
    "801610e9e92f990850ea4e7040613fe45fc3c7c9";


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

housingCfdConvRadMixedValueFvPatchScalarField::
housingCfdConvRadMixedValueFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const dictionary& dict
)
:
    mixedFvPatchField<scalar>(p, iF, dict)
{
    if (false)
    {
        Info<<"construct housingCfdConvRad sha1: 801610e9e92f990850ea4e7040613fe45fc3c7c9"
            " from patch/dictionary\n";
    }
}


housingCfdConvRadMixedValueFvPatchScalarField::
housingCfdConvRadMixedValueFvPatchScalarField
(
    const housingCfdConvRadMixedValueFvPatchScalarField& ptf,
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const fieldMapper& mapper
)
:
    mixedFvPatchField<scalar>(ptf, p, iF, mapper)
{
    if (false)
    {
        Info<<"construct housingCfdConvRad sha1: 801610e9e92f990850ea4e7040613fe45fc3c7c9"
            " from patch/DimensionedField/mapper\n";
    }
}


housingCfdConvRadMixedValueFvPatchScalarField::
housingCfdConvRadMixedValueFvPatchScalarField
(
    const housingCfdConvRadMixedValueFvPatchScalarField& ptf,
    const DimensionedField<scalar, volMesh>& iF
)
:
    mixedFvPatchField<scalar>(ptf, iF)
{
    if (false)
    {
        Info<<"construct housingCfdConvRad sha1: 801610e9e92f990850ea4e7040613fe45fc3c7c9 "
            "as copy/DimensionedField\n";
    }
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

housingCfdConvRadMixedValueFvPatchScalarField::
~housingCfdConvRadMixedValueFvPatchScalarField()
{
    if (false)
    {
        Info<<"destroy housingCfdConvRad sha1: 801610e9e92f990850ea4e7040613fe45fc3c7c9\n";
    }
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void housingCfdConvRadMixedValueFvPatchScalarField::updateCoeffs()
{
    if (this->updated())
    {
        return;
    }

    if (false)
    {
        Info<<"updateCoeffs housingCfdConvRad sha1: 801610e9e92f990850ea4e7040613fe45fc3c7c9\n";
    }

//{{{ begin code
    #line 31 "/home/cfd/cfd/u666_duty1/0/housing/T/boundaryField/defaultFaces"
const fvMesh& m = patch().boundaryMesh().mesh();
            if (!m.foundObject<volScalarField>("hExt"))
            {
                volScalarField* hp = new volScalarField
                (
                    IOobject("hExt", "0", m, IOobject::MUST_READ, IOobject::NO_WRITE),
                    m
                );
                hp->store();
            }
            const scalarField& h =
                m.lookupObject<volScalarField>("hExt").boundaryField()[patch().index()];
            const scalarField Tw(*this);
            const scalar Ta = 313.15, sigma = 5.670374e-8, eps = 0.1;
            const scalarField hr(eps*sigma*(sqr(Tw) + sqr(Ta))*(Tw + Ta));
            const scalarField kd(150*patch().deltaCoeffs());
            this->refValue() = Ta;
            this->refGrad() = 0;
            this->valueFraction() = (h + hr)/(h + hr + kd);
//}}} end code

    this->mixedFvPatchField<scalar>::updateCoeffs();
}


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace Foam

// ************************************************************************* //


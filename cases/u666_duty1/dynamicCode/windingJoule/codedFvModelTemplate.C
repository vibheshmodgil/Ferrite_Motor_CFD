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

#include "codedFvModelTemplate.H"
#include "addToRunTimeSelectionTable.H"
#include "volFields.H"
#include "surfaceFields.H"
#include "read.H"
#include "fvMatrix.H"

//{{{ begin codeInclude

//}}} end codeInclude


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

namespace fv
{

// * * * * * * * * * * * * * * * Local Functions * * * * * * * * * * * * * * //

//{{{ begin localCode

//}}} end localCode


// * * * * * * * * * * * * * * * Global Functions  * * * * * * * * * * * * * //

extern "C"
{
    // dynamicCode:
    // SHA1 = 95b65305a031c4bad772243555d3d6b75b32c2bf
    //
    // unique function name that can be checked if the correct library version
    // has been loaded
    void windingJoule_95b65305a031c4bad772243555d3d6b75b32c2bf(bool load)
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

defineTypeNameAndDebug(windingJouleFvModelscalarSource, 0);

addRemovableToRunTimeSelectionTable
(
    fvModel,
    windingJouleFvModelscalarSource,
    dictionary
);


const char* const windingJouleFvModelscalarSource::SHA1sum =
    "95b65305a031c4bad772243555d3d6b75b32c2bf";


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

windingJouleFvModelscalarSource::
windingJouleFvModelscalarSource
(
    const word& name,
    const word& modelType,
    const fvMesh& mesh,
    const dictionary& dict
)
:
    fvModel(name, modelType, mesh, dict),
    set_(mesh, coeffs())
{
    if (false)
    {
        Info<<"construct windingJoule sha1: 95b65305a031c4bad772243555d3d6b75b32c2bf"
            " from components\n";
    }
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

windingJouleFvModelscalarSource::
~windingJouleFvModelscalarSource()
{
    if (false)
    {
        Info<<"destroy windingJoule sha1: 95b65305a031c4bad772243555d3d6b75b32c2bf\n";
    }
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void windingJouleFvModelscalarSource::addSup
(
    const VolField<scalar>& field,
    fvMatrix<scalar>& eqn
) const
{
    if (false)
    {
        Info<<"windingJouleFvModelscalarSource::addSup()\n";
    }

//{{{ begin code
    
//}}} end code
}


void windingJouleFvModelscalarSource::addSup
(
    const volScalarField& rho,
    const VolField<scalar>& field,
    fvMatrix<scalar>& eqn
) const
{
    if (false)
    {
        Info<<"windingJouleFvModelscalarSource::addSup()\n";
    }

//{{{ begin code
    #line 15 "/home/cfd/cfd/u666_duty1/constant/winding/fvModels/windingJoule"
const scalarField& T = mesh().lookupObject<volScalarField>("T").primitiveField();
        const scalarField& V = mesh().V();
        scalarField& S = eqn.source();
        const char* zn[] = {"slot", "endw"};
        scalar Vz[2];
        for (int i = 0; i < 2; i++)
        {
            const labelList& cells = mesh().cellZones()[zn[i]];
            Vz[i] = 0;
            forAll(cells, j) Vz[i] += V[cells[j]];
            reduce(Vz[i], sumOp<scalar>());
        }
        const scalar fV = 0.4670408263649779*Vz[0] + 0.528*Vz[1];
        {
            const labelList& cells = mesh().cellZones()["slot"];
            const scalar qref = 1133.0000*0.4670408263649779/fV;   // W/m3 at T_ref
            const scalar qac = 6.4080/Vz[0];
            forAll(cells, j)
            {
                const label c = cells[j];
                S[c] -= V[c]*(qac + qref*(1.0 + 0.00393*(T[c] - 373.15)));
            }
        }
        {
            const labelList& cells = mesh().cellZones()["endw"];
            const scalar qref = 1133.0000*0.528/fV;   // W/m3 at T_ref
            const scalar qac = 0.0000/Vz[1];
            forAll(cells, j)
            {
                const label c = cells[j];
                S[c] -= V[c]*(qac + qref*(1.0 + 0.00393*(T[c] - 373.15)));
            }
        }
//}}} end code
}


void windingJouleFvModelscalarSource::addSup
(
    const volScalarField& alpha,
    const volScalarField& rho,
    const VolField<scalar>& field,
    fvMatrix<scalar>& eqn
) const
{
    if (false)
    {
        Info<<"windingJouleFvModelscalarSource::addSup()\n";
    }

//{{{ begin code
    
//}}} end code
}


bool windingJouleFvModelscalarSource::movePoints()
{
    set_.movePoints();
    return true;
}


void windingJouleFvModelscalarSource::topoChange(const polyTopoChangeMap& map)
{
    set_.topoChange(map);
}


void windingJouleFvModelscalarSource::mapMesh(const polyMeshMap& map)
{
    set_.mapMesh(map);
}


void windingJouleFvModelscalarSource::distribute
(
    const polyDistributionMap& map
)
{
    set_.distribute(map);
}


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace Foam
} // End namespace fv

// ************************************************************************* //


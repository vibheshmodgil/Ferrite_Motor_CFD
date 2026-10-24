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
    // SHA1 = 8e8f48a4bd1ea010440a0ca8cc1fd41d478b6dee
    //
    // unique function name that can be checked if the correct library version
    // has been loaded
    void windingJoule_8e8f48a4bd1ea010440a0ca8cc1fd41d478b6dee(bool load)
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
    "8e8f48a4bd1ea010440a0ca8cc1fd41d478b6dee";


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
        Info<<"construct windingJoule sha1: 8e8f48a4bd1ea010440a0ca8cc1fd41d478b6dee"
            " from components\n";
    }
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

windingJouleFvModelscalarSource::
~windingJouleFvModelscalarSource()
{
    if (false)
    {
        Info<<"destroy windingJoule sha1: 8e8f48a4bd1ea010440a0ca8cc1fd41d478b6dee\n";
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
    #line 15 "/home/cfd/cfd/duty1/constant/winding/fvModels/windingJoule"
const volScalarField& T = mesh().lookupObject<volScalarField>("T");
        const scalarField& V = mesh().V();
        const scalar qref = 579.5503/gSum(V);
        const scalar qac = 30.2351/gSum(V);
        eqn.source() -= V*(qac + qref*(1.0 + 0.00393*(T.primitiveField() - 373.15)));
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


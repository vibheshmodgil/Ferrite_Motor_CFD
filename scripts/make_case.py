"""Write an OpenFOAM-12 transient thermal case (foamMultiRun, all-solid regions) for one load point.

    python3 make_case.py <base_case> <case_dir> <loadpoint> [--h-file h_housing.json]

<base_case> holds the split mesh (constant/<region>/polyMesh).
The outside of the motor (patch defaultFaces of housing/shaft) gets natural convection h + radiation to ambient;
h is uniform (correlation) unless --h-file gives per-face values from the external-air CFD.
Runs inside WSL; stdlib only.
"""
import json, math, os, re, shutil, sys

base, case, lp = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
LP = json.load(open(os.path.join(HERE, "..", "loadpoints.json")))[lp]
HFILE = sys.argv[sys.argv.index("--h-file") + 1] if "--h-file" in sys.argv else None

T_AMB = 313.15          # 40 C ambient and start temperature
H_NAT = 6.0             # W/m2K, finned housing in still air (replaced by --h-file from the CFD)
EMISSIVITY = float(os.environ.get("EMISSIVITY", 0.7))   # 0.7 painted; user 2026-10-21: bare machined Al ~0.1 (fin study)
END_TIME = LP.get("end_time", 250 if lp == "peak_torque" else 12 * 3600)  # s; natural convection settles slowly
DT = LP.get("dt", 1 if lp == "peak_torque" else 120)                      # s
WRITE = LP.get("write", 50 if lp == "peak_torque" else 3600)

# rho [kg/m3], Cv [J/kg/K], kappa [W/m/K] (scalar, or (x y z) diagonal in the region/zone frame)
MAT = {
    "housing":  (2680, 900, 150),                 # AlSi10Mg
    "stator":   (7650, 460, (28, 28, 1.5)),       # M235-35A stack: in-plane / across laminations
    "rotor":    (7650, 460, (28, 28, 1.5)),
    "magnets":  (4900, 800, 4.0),                 # sintered ferrite
    "shaft":    (7850, 460, 45),
    "bearings": (7850, 460, 15),                  # ponytail: solid ring with reduced k for the ball contacts
    # Cu fill 0.51 (12 x 14.9 cm3 of wire in 348 cm3 of block) + impregnation resin
    # ponytail: isotropic 1.0 W/mK (cross-turn 0.77 plus a little wire-direction path). OpenFOAM's anisotropic
    # model with per-coil frames (0.77 / 200 along the wire) diverged on this tet mesh even at 20:1
    "winding":  (0.51 * 8933 + 0.49 * 1200, None, 1.0),
    "inair":    (10.0, 718, LP["k_inair"]),       # end-space convection as an effective conductivity;
                                                  # ponytail: rho x10 (12 J/K vs ~7 kJ/K motor) keeps coupling calm
}
# verification switches (energy_test.sh): ISO_STEEL=<k> isotropic laminations, ADIABATIC=1 no outer heat loss,
# JOULE_TC=0 temperature-independent copper loss
if os.environ.get("ISO_STEEL"):
    for r in ("stator", "rotor"):
        MAT[r] = (MAT[r][0], MAT[r][1], float(os.environ["ISO_STEEL"]))
ADIABATIC = os.environ.get("ADIABATIC") == "1"
JOULE_TC = float(os.environ.get("JOULE_TC", 0.00393))
cp_w = (0.51 * 8933 * 385 + 0.49 * 1200 * 1500) / MAT["winding"][0]
MAT["winding"] = (MAT["winding"][0], cp_w, MAT["winding"][2])
# detailed model (real geometry). The CAD wire is 3.0 mm over enamel; build_mesh_detailed.py sweeps the bare 2.9 mm
# copper (R_WIRE 1.45), so the coil region is pure Cu and the 0.05 mm enamel shell is meshed as resin (0.25 ~ 0.22).
f_cu = 1.0
MAT.update({
    "coil":   (f_cu * 8933 + (1 - f_cu) * 1400, (f_cu * 8933 * 385 + (1 - f_cu) * 1400 * 1100) /
               (f_cu * 8933 + (1 - f_cu) * 1400), round(f_cu * 390)),
    "bobbin": (1350, 1500, 0.35),                 # PA66-GF30 (bobbin and gland material in the project CAD)
    "resin":  (1200, 1500, 0.25),                 # impregnation varnish / epoxy, void-free
    "busbar": (8933, 385, 390),                   # Cu-ETP
    "strap":  (8933, 385, 390),
    "tbar":   (8933, 385, 390),
    "copper": (8933, 385, 390),                   # coil+strap+busbar+tbar as one region (MERGE_CU); parts are cellZones
})

# contact layers (thickness m, kappa W/m/K) on region pairs
LAYERS = {
    # no enamel layer on coil patches: the enamel is in the meshed gap (see f_cu)
    frozenset(("winding", "stator")): (1.7e-3, 0.30),    # bobbin wall + resin gap (neck 7.2 -> coil 8.9 mm)
    frozenset(("stator", "housing")): (2e-5, 0.026),     # shrink fit, ~1300 W/m2K
    frozenset(("magnets", "rotor")): (1e-4, 0.20),       # glue
    frozenset(("rotor", "stator")): (5e-4, LP["k_gap"]), # air gap, Taylor-Couette effective conductivity
}

HDR = 'FoamFile\n{\n    format      ascii;\n    class       %s;\n    object      %s;\n}\n'


def write(path, body, cls="dictionary"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(HDR % (cls, os.path.basename(path)) + body)


def patches(region):
    txt = open(os.path.join(case, "constant", region, "polyMesh", "boundary")).read()
    return re.findall(r"^\s{4}(\w+)\s*\n\s{4}\{", txt, re.M)


if os.path.exists(case):
    shutil.rmtree(case)
os.makedirs(case)
shutil.copytree(os.path.join(base, "constant"), os.path.join(case, "constant"))
regions = sorted(d for d in os.listdir(os.path.join(case, "constant"))
                 if os.path.isdir(os.path.join(case, "constant", d, "polyMesh")))
assert set(regions) <= set(MAT), regions
for r in regions:   # outer skin as a wall, so the Qout_* wallHeatFlux monitors report it (same as wallify.py)
    bf = os.path.join(case, "constant", r, "polyMesh", "boundary")
    t = open(bf).read()
    open(bf, "w").write(re.sub(r"(\n    defaultFaces\n    \{[^}]*?type\s+)patch;", r"\1wall;", t))
CU_ZONES = ("coil", "strap", "busbar", "tbar") if "copper" in regions else ()
if ("coil" in regions or CU_ZONES) and lp != "peak_torque" and "dt" not in LP:
    DT = 300     # detailed model (~3x the cells): 5-minute steps over the 12 h runs

# ---------------------------------------------------------------- system
write(f"{case}/system/controlDict", f"""
application     foamMultiRun;
regionSolvers
{{
{''.join(f'    {r:10s} solid;{chr(10)}' for r in regions)}}}
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {END_TIME};
deltaT          {DT};
adjustTimeStep  no;          // implicit conduction: fixed step, stable at any diffusion number
writeControl    adjustableRunTime;
writeInterval   {WRITE};
purgeWrite      0;
writeFormat     binary;
timeFormat      general;
timePrecision   8;
runTimeModifiable yes;
functions
{{
{''.join(f'''    T_{r}
    {{
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        region          {r};
        select          all;
        fields          (T);
        operation       {op};
        writeFields     false;
        writeControl    timeStep;
        writeInterval   1;
        log             false;
    }}
''' for r in regions for op in ['max'])}{''.join(f'''    T_{z}
    {{
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        region          copper;
        select          cellZone;
        cellZone        {z};
        fields          (T);
        operation       {op};
        writeFields     false;
        writeControl    timeStep;
        writeInterval   1;
        log             false;
    }}
''' for z in CU_ZONES for op in ['max'])}{''.join(f'''    Tavg_{z}
    {{
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        region          copper;
        select          cellZone;
        cellZone        {z};
        fields          (T);
        operation       volAverage;
        writeFields     false;
        writeControl    timeStep;
        writeInterval   1;
        log             false;
    }}
''' for z in CU_ZONES[:1])}{''.join(f'''    Tavg_{r}
    {{
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        region          {r};
        select          all;
        fields          (T);
        operation       volAverage;
        writeFields     false;
        writeControl    timeStep;
        writeInterval   1;
        log             false;
    }}
''' for r in ('winding', 'coil', 'magnets', 'housing') if r in regions)}{''.join(f'''    Qout_{r}
    {{
        type            wallHeatFlux;     // heat through the outer skin every step, for the global energy balance
        libs            ("libfieldFunctionObjects.so");
        region          {r};
        patches         (defaultFaces);
        objects         ();               // only the .dat log: the default also writes the field every step
        writeControl    timeStep;
        writeInterval   1;
        log             false;
    }}
''' for r in ('housing', 'shaft') if r in regions)}}}
""")
# foamMultiRun couples the regions segregated (Gauss-Seidel over regions; each sees its neighbours' last iterate).
# Unconverged, the two sides of an interface disagree on the flux and a heating transient destroys energy:
# adiabatic test (energy_test.sh) -49 % with 1-2 outer correctors, -3.6 % with 10. So iterate the outer loop
# to a residual tolerance: 1e-3 gives -0.2 %. OUTER_TOL is the knob: tighter = closer conservation, slower.
# The housing gets a 20x looser test: its residual stalls near 1e-3 on its own deferred non-orthogonal correction
# (finned tets; conservative inside the region), and its coupling shows in the neighbours' residuals anyway.
OUTER_TOL = float(os.environ.get("OUTER_TOL", 1e-3))
write(f"{case}/system/fvSolution", "PIMPLE\n{\n    nOuterCorrectors 100;\n}\n")
write(f"{case}/system/decomposeParDict", f"numberOfSubdomains {os.environ.get('NP', 4)};\nmethod scotch;\n")   # NP: MPI ranks
for r in regions:
    # strongly anisotropic regions on tets: the explicit non-orthogonal/cross term goes unstable -> uncorrected
    corr = "uncorrected" if isinstance(MAT[r][2], tuple) else "limited corrected 0.5"
    write(f"{case}/system/{r}/fvSchemes", f"""
ddtSchemes {{ default Euler; }}
gradSchemes {{ default Gauss linear; }}
divSchemes {{ default none; }}
laplacianSchemes {{ default Gauss linear {corr}; }}
interpolationSchemes {{ default linear; }}
snGradSchemes {{ default {corr}; }}
""")
    write(f"{case}/system/{r}/fvSolution", """
solvers
{
    e { solver GAMG; smoother DICGaussSeidel; tolerance 1e-7; relTol 0.1; }   // inner: the outer loop converges it
    eFinal { solver GAMG; smoother DICGaussSeidel; tolerance 1e-7; relTol 0; }
}
PIMPLE
{
    nNonOrthogonalCorrectors 0;       // the outer iterations update the explicit correction anyway
    outerCorrectorResidualControl { e { tolerance %g; relTol 0; } }
}
""" % (20 * OUTER_TOL if r == "housing" else OUTER_TOL))
    shutil.copy(f"{case}/system/decomposeParDict", f"{case}/system/{r}/decomposeParDict")

# ---------------------------------------------------------------- materials
for r in regions:
    rho, cv, k = MAT[r]
    aniso = isinstance(k, tuple)
    kap = (f"Kappa\n{{\n    type uniform;\n    value ({k[0]} {k[1]} {k[2]});\n}}\n" if aniso
           else f"kappa\n{{\n    type uniform;\n    value {k};\n}}\n")
    write(f"{case}/constant/{r}/physicalProperties",
          f"thermoType {'constAnisoSolidThermo' if aniso else 'constSolidThermo'};\n"
          f"rho\n{{\n    type uniform;\n    value {rho};\n}}\nCv\n{{\n    type uniform;\n    value {cv:.1f};\n}}\n" + kap)
    if aniso:
        write(f"{case}/constant/{r}/thermophysicalTransport", f"""
model anisotropic;
boundaryAligned true;
coordinateSystem
{{
    type cartesian;
    origin (0 0 0);
    coordinateRotation {{ type axesRotation; e1 (1 0 0); e3 (0 0 1); }}
}}
""")

# ---------------------------------------------------------------- heat sources
Q = LP["Q"]
RHO20 = 1.72e-8          # Cu resistivity at 20 C, ohm m
# Joule sources rise with resistance, q = q_ref (1 + 0.00393 (T - T_ref)), evaluated per cell every step.
# q_ref per cell: a total W spread over the region volume, or rho J^2 where the conductor section is uniform.
JOULE = {
    "winding": (f"{Q['winding_100C']:.4f}/gSum(V)", 373.15),          # FEMM copper loss at 100 C
    "coil":    (f"{Q['winding_100C']:.4f}/gSum(V)", 373.15),          # same, in the real wire (DC: uniform J)
    "busbar":  (f"{LP.get('busbar_20C', 0):.4f}/gSum(V)", 293.15),    # busbar study: 28.25 W at 360 A, 20 C
    "strap":   (f"{RHO20}*sqr({LP.get('J_strap', 0):.6g})", 293.15),  # path current in 4.5 x 2 mm
    "tbar":    (f"{RHO20}*sqr({LP.get('J_tbar', 0):.6g})", 293.15),   # line current in 3 x 10 mm
}
QAC = Q.get("winding_ac", 0.0)   # AC copper loss (proximity/skin), W: constant, uniform, not temperature-scaled
for r in regions:
    if r in JOULE:
        qref, tref = JOULE[r]
        qac = QAC if r in ("winding", "coil") else 0.0
        write(f"{case}/constant/{r}/fvModels", f"""
{r}Joule
{{
    type            coded;
    select          all;
    field           e;
    codeAddRhoSup
    #{{
        const volScalarField& T = mesh().lookupObject<volScalarField>("T");
        const scalarField& V = mesh().V();
        const scalar qref = {qref};
        const scalar qac = {qac:.4f}/gSum(V);
        eqn.source() -= V*(qac + qref*(1.0 + {JOULE_TC}*(T.primitiveField() - {tref})));
    #}};
}}
""")
    elif r == "copper":   # one coded source looping over the part zones, same q_ref/T_ref as the split regions
        # ponytail: one fvModel, not one per zone: 4 coded models in one region aborted the parallel run (ranks 1-2)
        src = ""
        for z in CU_ZONES:
            qref, tref = JOULE[z]
            qac = QAC if z == "coil" else 0.0
            src += f"""
        {{
            const labelList& cells = mesh().cellZones()["{z}"];
            scalar Vz = 0;
            forAll(cells, i) Vz += V[cells[i]];
            reduce(Vz, sumOp<scalar>());
            const scalar qref = {qref.replace("gSum(V)", "Vz")};
            const scalar qac = {qac:.4f}/Vz;
            forAll(cells, i)
            {{
                const label c = cells[i];
                S[c] -= V[c]*(qac + qref*(1.0 + {JOULE_TC}*(T[c] - {tref})));
            }}
        }}"""
        write(f"{case}/constant/{r}/fvModels", f"""
copperJoule
{{
    type            coded;
    select          all;
    field           e;
    codeAddRhoSup
    #{{
        const scalarField& T = mesh().lookupObject<volScalarField>("T").primitiveField();
        const scalarField& V = mesh().V();
        scalarField& S = eqn.source();{src}
    #}};
}}
""")
    elif Q.get(r, 0) > 0:
        write(f"{case}/constant/{r}/fvModels", f"""
loss
{{
    type    heatSource;
    select  all;
    Q       {Q[r]:.4f};
}}
""")

# ---------------------------------------------------------------- T boundary conditions
hlist = json.load(open(HFILE)) if HFILE else {}
for r in regions:
    bc = ""
    for p in patches(r):
        m = re.match(r"(\w+)_to_(\w+)$", p)
        if m and m.group(1) == r:
            lay = LAYERS.get(frozenset((r, m.group(2))))
            extra = (f"        thicknessLayers ({lay[0]});\n        kappaLayers ({lay[1]});\n") if lay else ""
            bc += f"    {p}\n    {{\n        type coupledTemperature;\n{extra}        value $internalField;\n    }}\n"
        elif p == "defaultFaces" and ADIABATIC:
            bc += f"    {p}\n    {{\n        type zeroGradient;\n    }}\n"
        elif p == "defaultFaces" and r in ("housing", "shaft") and p in hlist.get(r, {}):
            # per-face CFD h + radiation to ambient. OpenFOAM's externalTemperature takes only a uniform h, so:
            # mixed BC, f = (h + h_rad) / (h + h_rad + kappa |delta|^-1), h_rad = eps sigma (Tw^2+Ta^2)(Tw+Ta),
            # h read per face from the field hExt (0/<region>/hExt, decomposed with the case)
            hv = hlist[r][p]
            write(f"{case}/0/{r}/hExt", "dimensions [1 0 -3 -1 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n"
                  f"    {p}\n    {{\n        type calculated;\n        value nonuniform List<scalar> {len(hv)}("
                  + " ".join(f"{v:.4g}" for v in hv) + ");\n    }\n    \".*\"\n    {\n        type calculated;\n"
                  "        value uniform 0;\n    }\n}\n", cls="volScalarField")
            ev = hlist[r].get("eps_" + p)   # fin_eps.py: per-face factor, radiation only through the fin envelope
            if ev:
                write(f"{case}/0/{r}/epsExt", "dimensions [0 0 0 0 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n"
                      f"    {p}\n    {{\n        type calculated;\n        value nonuniform List<scalar> {len(ev)}("
                      + " ".join(f"{EMISSIVITY * v:.4g}" for v in ev) + ");\n    }\n    \".*\"\n    {\n        type calculated;\n"
                      "        value uniform 0;\n    }\n}\n", cls="volScalarField")
            epsc = ("""const scalarField& eps =
                m.lookupObject<volScalarField>("epsExt").boundaryField()[patch().index()];""" if ev else
                    f"const scalar eps = {EMISSIVITY};")
            epsr = ("""if (!m.foundObject<volScalarField>("epsExt"))
            {
                volScalarField* ep = new volScalarField
                (
                    IOobject("epsExt", "0", m, IOobject::MUST_READ, IOobject::NO_WRITE),
                    m
                );
                ep->store();
            }""" if ev else "")
            kap = MAT[r][2]
            bc += f"""    {p}
    {{
        type            codedMixed;
        name            {r}CfdConvRad;
        refValue        uniform {T_AMB};
        refGradient     uniform 0;
        valueFraction   uniform 0;
        value           $internalField;
        code
        #{{
            const fvMesh& m = patch().boundaryMesh().mesh();
            if (!m.foundObject<volScalarField>("hExt"))
            {{
                volScalarField* hp = new volScalarField
                (
                    IOobject("hExt", "0", m, IOobject::MUST_READ, IOobject::NO_WRITE),
                    m
                );
                hp->store();
            }}
            {epsr}
            const scalarField& h =
                m.lookupObject<volScalarField>("hExt").boundaryField()[patch().index()];
            const scalarField Tw(*this);
            const scalar Ta = {T_AMB}, sigma = 5.670374e-8;
            {epsc}
            const scalarField hr(eps*sigma*(sqr(Tw) + sqr(Ta))*(Tw + Ta));
            const scalarField kd({kap}*patch().deltaCoeffs());
            this->refValue() = Ta;
            this->refGrad() = 0;
            this->valueFraction() = (h + hr)/(h + hr + kd);
        #}};
    }}
"""
        elif p == "defaultFaces" and r in ("housing", "shaft"):
            bc += (f"    {p}\n    {{\n        type externalTemperature;\n        Ta constant {T_AMB};\n"
                   f"        h uniform {H_NAT};\n        emissivity {EMISSIVITY};\n        value $internalField;\n    }}\n")
        else:      # cut faces of the cavity at gland holes / shaft bore: adiabatic
            bc += f"    {p}\n    {{\n        type zeroGradient;\n    }}\n"
    write(f"{case}/0/{r}/T", f"dimensions [0 0 0 1 0 0 0];\ninternalField uniform {T_AMB};\nboundaryField\n{{\n{bc}}}\n",
          cls="volScalarField")
print("wrote", case, "regions:", " ".join(regions))

"""U666: write an OpenFOAM-12 transient thermal case (foamMultiRun, all-solid regions) for one load point.

    python3 u666_make_case.py <base_case> <case_dir> <loadpoint> [--lp-file u666_loadpoints.json] [--h-file h.json]

Copy of make_case.py for the U666 CAD (regions from u666_geo.py). Load point JSON, keyed by name:
  {"<lp>": {"Q": {"winding_dc": W at T_ref, "winding_ac": W, "stator": W, "rotor": W, "magnets": W,
                  "bearings": W, "inair": W},
            "T_ref": 373.15, "k_gap": W/mK, "k_inair": W/mK, "end_time": s, "dt": s, "write": s}}
Winding DC rises with T: q = q_ref (1 + 0.00393 (T - T_ref)); spread over the cellZones slot/endw in proportion
to their copper fill (uniform current density). AC loss is constant and in the slot zone only.
Env switches: ADIABATIC=1, JOULE_TC=0 (energy test), EMISSIVITY (default 0.1), WIND_ISO=1 (isotropic winding).
"""
import json, math, os, re, shutil, sys

base, case, lp = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
LPF = sys.argv[sys.argv.index("--lp-file") + 1] if "--lp-file" in sys.argv else os.path.join(HERE, "..", "loadpoints_u666.json")
LP = json.load(open(LPF))[lp]
HFILE = sys.argv[sys.argv.index("--h-file") + 1] if "--h-file" in sys.argv else None

# ---- loss-split parameters (pending from the user's EMAG; env overrides)
IRON_STATOR_FRAC = float(os.environ.get("IRON_STATOR_FRAC", 0.8))   # Q_iron -> stator / rotor
BRG_FRONT_FRAC = float(os.environ.get("BRG_FRONT_FRAC", 0.5))       # Q_friction -> front / rear bearing
T_REF_C = float(os.environ.get("T_REF_C", 100.0))                    # copper DC loss reference temperature
GAP, R_ROT = 6.5e-4, 0.04288                                          # m, U666 air gap and rotor radius
DT_BY_LP = {"duty1": 3, "duty2": 10, "duty3": 20, "duty4": 60, "duty5": 60}   # s (old-CAD practice)


def gap_k(rpm):      # Taylor-Couette effective conductivity of the gap (loadpoints_9795.py, U666 radii)
    w = rpm * 2 * math.pi / 60
    ta = w * w * (R_ROT + GAP / 2) * GAP ** 3 / 2.1e-5 ** 2
    nu = 2.0 if ta < 1740 else 0.128 * ta ** 0.367 if ta < 1e4 else 0.409 * ta ** 0.241
    return 0.030 * nu / 2


def endspace_k(rpm):  # end-space h (Motor-CAD style) x 10 mm, as an effective conductivity
    return (15 + 6.75 * (rpm * 2 * math.pi / 60 * R_ROT) ** 0.65) * 0.010


if "Q_cu_dc_W" in LP:   # loadpoints_u666.json (Motor-CAD) -> per-region losses
    fi, fb = IRON_STATOR_FRAC, BRG_FRONT_FRAC
    t_end = LP["target_min"] * 60
    dt = DT_BY_LP.get(lp, max(1, round(t_end / 100)))
    LP = dict(Q={"winding_dc": LP["Q_cu_dc_W"], "winding_ac": LP["Q_cu_ac_W"], "stator": fi * LP["Q_iron_W"],
                 "rotor": (1 - fi) * LP["Q_iron_W"], "magnets": LP["Q_magnet_W"], "inair": LP["Q_windage_W"],
                 "bearing_f": fb * LP["Q_friction_W"], "bearing_r": (1 - fb) * LP["Q_friction_W"]},
              T_ref=273.15 + T_REF_C, k_gap=gap_k(LP["rpm"]), k_inair=endspace_k(LP["rpm"]), gap=GAP,
              end_time=t_end, dt=dt, write=dt * max(1, round(t_end / dt / 10)))

T_AMB = 313.15
H_NAT = 5.0                     # W/m2K, uniform fallback when no --h-file
EMISSIVITY = float(os.environ.get("EMISSIVITY", 0.1))   # bare machined Al (user 2026-10-21)
END_TIME, DT, WRITE = LP.get("end_time", 12 * 3600), LP.get("dt", 60), LP.get("write", 3600)

# ---- the winding homogenisation: ONE dict (main agent: final values go here) ----------------------------------
# Motor-CAD (user, 2026-10-22): slot 97.57 mm2, winding 85.54 mm2 (96.67 with liner), Cu 47.51 mm2 (120 x 0.71 mm).
# Kappa in the global cylindrical frame (r, theta, z): slot wire along z, end-winding wire along theta.
# The meshed slot winding fills the CAD slot minus wedge (A_SLOT_MESH, incl. the 0.25 mm liner space; liner = contact
# layer below), so rho and the copper fraction are scaled by 85.54/A_SLOT_MESH: copper mass and heat capacity exact.  ponytail: k_T left as given for the 85.54 mm2 bundle.
A_SLOT_MESH = 101.65   # mm2 per slot actually meshed (u666_geo: slot 221.58 cm3 / 36 / 60.55 mm; CAD slot - wedge)
WINDING = {
    "slot": dict(fill=0.555 * 85.54 / A_SLOT_MESH, rho=5510 * 85.54 / A_SLOT_MESH, cv=473, k=(1.12, 1.12, 217.0 * 85.54 / A_SLOT_MESH)),   # axial conductance kept
    "endw": dict(fill=0.528, rho=5510, cv=473, k=(1.05, 205.0, 205.0)),   # wire in the theta-z sheet (approved)
}
if os.environ.get("WIND_ISO"):   # fallback (KNOWN_ISSUES #3): isotropic-equivalent per zone
    for z in WINDING.values():
        z["k"] = (float(os.environ["WIND_ISO"]),) * 3 if os.environ["WIND_ISO"] != "1" else (z["k"][0],) * 3

# rho [kg/m3], Cv [J/kg/K], kappa [W/m/K] scalar or (x y z) diagonal (laminations: frame = global cartesian)
MAT = {
    "housing":  (2680, 900, 150),                 # cast Al, machined (+ rear cover, seats, gasket)
    "stator":   (7650, 460, (28, 28, 1.5)),       # lamination stack: in-plane / axial
    "rotor":    (7650, 460, (28, 28, 1.5)),
    "magnets":  (7500, 440, 9),                   # NdFeB
    "endcaps":  (8470, 380, 115),                 # brass (+ steel nut, ponytail: 2 cm3)
    "shaft":    (7850, 460, 45),
    "bearings": (7850, 460, 15),                  # solid ring, reduced k for ball contacts
    "wedge":    (1350, 1500, 0.2),                # slot wedge + slot opening
    "winding":  None,                             # zonal, from WINDING
    "inair":    (10.0, 718, LP["k_inair"]),       # end space as effective conductivity; rho x10 for coupling calm
}
if os.environ.get("ROTOR_ISO"):   # anisotropic rotor stack gives an indefinite matrix on the nc mesh (S8): isotropic k instead
    MAT["rotor"] = (7650, 460, float(os.environ["ROTOR_ISO"]))
if os.environ.get("STATOR_ISO"):   # diagnostic (BASE2): isotropic stator stack
    MAT["stator"] = (7650, 460, float(os.environ["STATOR_ISO"]))
ADIABATIC = os.environ.get("ADIABATIC") == "1"
JOULE_TC = float(os.environ.get("JOULE_TC", 0.00393))

# contact layers (thickness m, kappa W/m/K) on region pairs
LAYERS = {
    frozenset(("winding", "stator")): (2.5e-4, 2.5e-4 / 1.67e-3),   # slot liner, R = 1.67e-3 m2K/W (Motor-CAD)
    frozenset(("stator", "housing")): (2e-5, 0.026),                 # shrink fit
    frozenset(("magnets", "rotor")): (1e-4, 0.20),                   # glue
    frozenset(("rotor", "stator")): (LP.get("gap", 5e-4), LP["k_gap"]),   # air gap (rotor grown to the bore)
    frozenset(("rotor", "wedge")): (LP.get("gap", 5e-4), LP["k_gap"]),
    frozenset(("endcaps", "stator")): (LP.get("gap", 5e-4), LP["k_gap"]),
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
SKIN = ("housing", "shaft")
for r in regions:   # outer skin as a wall, so wallHeatFlux reports it
    bf = os.path.join(case, "constant", r, "polyMesh", "boundary")
    t = open(bf).read()
    t = re.sub(r"(\n    defaultFaces\n    \{[^}]*?type\s+)patch;", r"\1wall;", t)
    t = re.sub(r"(method\s+intersection;[^\n]*\n)", r"\1        matchTolerance 0.5;   // nc interfaces: centre-of-patch check relaxed (area mismatch accepted)\n", t)
    open(bf, "w").write(t)


def fo(name, region, op, extra="select all;"):
    return f"""    {name}
    {{
        type volFieldValue; libs ("libfieldFunctionObjects.so"); region {region}; {extra}
        fields (T); operation {op}; writeFields false; writeControl timeStep; writeInterval 5; log false;
    }}
"""


# cut-plane outputs (vtk, cell values per region, every 10 steps = 10 s at dt 1). z: stack -0.35..60.2, EW 60.2..90.15 / -30.3..-0.35
PLANES = {"axial_y0": ((0, 0, 0), (0, 1, 0), None),
          "radial_stack": ((0, 0, 29.9), (0, 0, 1), ["housing", "stator", "winding", "wedge", "rotor", "magnets", "shaft", "inair"]),
          "radial_ew_front": ((0, 0, 75.0), (0, 0, 1), ["housing", "winding", "inair", "shaft", "endcaps"]),
          "radial_ew_rear": ((0, 0, -15.3), (0, 0, 1), ["housing", "winding", "inair", "shaft", "endcaps"])}


def surf(pn, r):
    (p, n, _) = PLANES[pn]
    return f"""    S_{pn}_{r}
    {{
        type surfaces; libs ("libsampling.so"); region {r}; writeControl timeStep; writeInterval 10; log false;
        surfaceFormat vtk; interpolationScheme cell; fields (T);
        surfaces ( {pn} {{ type cutPlane; planeType pointAndNormal; interpolate false; point ({p[0]*1e-3:.6g} {p[1]*1e-3:.6g} {p[2]*1e-3:.6g}); normal ({n[0]} {n[1]} {n[2]}); }} );
    }}
"""


funcs = "".join(fo(f"T_{r}", r, "max") for r in regions) + "".join(fo(f"Tmin_{r}", r, "min") for r in regions)
funcs += "".join(surf(pn, r) for pn, (_, _, rl) in PLANES.items() for r in regions if rl is None or r in rl)
funcs += "".join(fo(f"Tavg_{r}", r, "volAverage") for r in regions)
ZONED = {"winding": list(WINDING), "rotor": ["rotor", "rpocket"]}   # regions whose rho cv differ per cellZone
funcs += "".join(fo(f"Tint_{r}", r, "volIntegrate") for r in regions)
funcs += "".join(fo(f"Tavgz_{z}", r, "volAverage", f"select cellZone; cellZone {z};") + fo(f"Tintz_{z}", r, "volIntegrate", f"select cellZone; cellZone {z};") for r in regions if r in ZONED for z in ZONED[r])
funcs += "".join(fo(f"T_{z}", "winding", "max", f"select cellZone; cellZone {z};") for z in WINDING)
funcs += "".join(f"""    Qout_{r}
    {{
        type wallHeatFlux; libs ("libfieldFunctionObjects.so"); region {r}; patches (defaultFaces);
        objects (); writeControl timeStep; writeInterval 1; log false;
    }}
""" for r in SKIN if r in regions)
funcs += "".join(f"""    Qif_{r}
    {{
        type wallHeatFlux; libs ("libfieldFunctionObjects.so"); region {r}; patches ("{r}_to_.*");
        objects (); writeControl timeStep; writeInterval 1; log false;
    }}
""" for r in regions)   # per-interface heat (BASE2): the two sides of each mapped pair must sum to ~0
write(f"{case}/system/controlDict", f"""
application     foamMultiRun;
libs            ("libcoupledTemperatureNC.so");
regionSolvers
{{
{''.join(f'    {r:10s} solid;{chr(10)}' for r in sorted(regions, key=lambda r: r != "winding"))}}}   // winding (fastest-rising T) solved first: smaller coupling lag
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {END_TIME};
deltaT          {DT};
adjustTimeStep  no;
writeControl    adjustableRunTime;
writeInterval   {WRITE};
purgeWrite      0;
writeFormat     binary;
timeFormat      general;
timePrecision   8;
runTimeModifiable yes;
functions
{{
{funcs}}}
""")
OUTER_TOL = float(os.environ.get("OUTER_TOL", 1e-3))   # KNOWN_ISSUES #1: converge the region coupling
write(f"{case}/system/fvSolution", "PIMPLE\n{\n    nOuterCorrectors 100;\n}\n")
write(f"{case}/system/decomposeParDict", f"numberOfSubdomains {os.environ.get('NP', 4)};\nmethod scotch;\n")
for r in regions:
    aniso = r == "winding" or isinstance(MAT[r][2], tuple)
    corr = "uncorrected" if aniso else "limited corrected 0.33"
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
    e { solver GAMG; smoother DICGaussSeidel; tolerance 1e-7; relTol 0.1; }
    eFinal { solver GAMG; smoother DICGaussSeidel; tolerance 1e-7; relTol 0; }
}
PIMPLE
{
    nNonOrthogonalCorrectors 1;
    outerCorrectorResidualControl { e { tolerance %g; relTol 0; } }
}
""" % (20 * OUTER_TOL if r == "housing" else OUTER_TOL))
    shutil.copy(f"{case}/system/decomposeParDict", f"{case}/system/{r}/decomposeParDict")

# ---------------------------------------------------------------- materials
CS = {"cartesian": "coordinateRotation { type axesRotation; e1 (1 0 0); e3 (0 0 1); }",
      "cylindrical": "coordinateRotation { type cylindrical; e3 (0 0 1); }"}


def prop(name, vals, vec=False):
    """uniform, or zonal over the winding cellZones."""
    if not isinstance(vals, dict):
        v = f"({vals[0]} {vals[1]} {vals[2]})" if vec else f"{vals}"
        return f"{name}\n{{\n    type uniform;\n    value {v};\n}}\n"
    fmt = (lambda k: f"({k[0]:.4g} {k[1]:.4g} {k[2]:.4g})") if vec else (lambda k: f"{k:.6g}")
    first = next(iter(vals.values()))
    return (f"{name}\n{{\n    type zonal;\n    value {fmt(first)};\n    zones\n    {{\n"
            + "".join(f"        {z} {fmt(v)};\n" for z, v in vals.items()) + "    }\n}\n")


# air in the magnet pockets: same Cv as the rotor iron (zonal Cv jumps blow up the nc coupling, S8), rho scaled to keep rho*Cv of air
RPOCKET = (1.2 * 1007 / MAT["rotor"][1], MAT["rotor"][1], 0.03)


def has_zone(r, z):
    f = os.path.join(case, "constant", r, "polyMesh", "cellZones")
    return os.path.exists(f) and re.search(r"\n%s\s*\n\s*\{" % z, open(f).read()) is not None


PROPS = {}
for r in regions:
    if r == "winding":
        rho = {z: w["rho"] for z, w in WINDING.items()}
        cv = {z: w["cv"] for z, w in WINDING.items()}
        k, frame = {z: w["k"] for z, w in WINDING.items()}, "cylindrical"
    elif r == "rotor" and has_zone("rotor", "rpocket"):   # air left in the magnet pockets: still air
        z2 = {"rotor": MAT["rotor"], "rpocket": RPOCKET}
        rho, cv = ({z: m[i] for z, m in z2.items()} for i in (0, 1))
        k = {z: m[2] if isinstance(m[2], tuple) else (m[2],) * 3 for z, m in z2.items()}
        frame = "cartesian"
    else:
        rho, cv, k = MAT[r]
        frame = "cartesian"
    PROPS[r] = {z: rho[z] * cv[z] for z in rho} if isinstance(rho, dict) else rho * cv
    aniso = r == "winding" or isinstance(k, tuple) or (isinstance(k, dict) and any(isinstance(v, tuple) for v in k.values()))
    write(f"{case}/constant/{r}/physicalProperties",
          f"thermoType {'constAnisoSolidThermo' if aniso else 'constSolidThermo'};\n"
          + prop("rho", rho) + prop("Cv", cv) + prop("Kappa" if aniso else "kappa", k, vec=aniso))
    if aniso:
        write(f"{case}/constant/{r}/thermophysicalTransport", f"""
model anisotropic;
boundaryAligned true;
coordinateSystem
{{
    type cartesian;
    origin (0 0 0);
    {CS[frame]}
}}
""")

json.dump(dict(rhocv=PROPS, Q=LP["Q"], T_ref=LP.get("T_ref", 373.15), tc=JOULE_TC, T0=T_AMB,
               fill={z: w["fill"] for z, w in WINDING.items()}, skin=[r for r in SKIN if r in regions]),
          open(f"{case}/case_props.json", "w"), indent=1)
# ---------------------------------------------------------------- heat sources
Q = LP["Q"]
T_REF = LP.get("T_ref", 373.15)
if "winding" in regions:
    src = ""
    fills = " + ".join(f"{w['fill']}*Vz[{i}]" for i, w in enumerate(WINDING.values()))
    for i, (z, w) in enumerate(WINDING.items()):
        qac = Q.get("winding_ac", 0.0) if z == "slot" else 0.0
        src += f"""
        {{
            const labelList& cells = mesh().cellZones()["{z}"];
            const scalar qref = {Q.get('winding_dc', 0.0):.4f}*{w['fill']}/fV;   // W/m3 at T_ref
            const scalar qac = {qac:.4f}/Vz[{i}];
            forAll(cells, j)
            {{
                const label c = cells[j];
                S[c] -= V[c]*(qac + qref*(1.0 + {JOULE_TC}*(T[c] - {T_REF})));
            }}
        }}"""
    write(f"{case}/constant/winding/fvModels", f"""
windingJoule
{{
    type            coded;
    select          all;
    field           e;
    codeAddRhoSup
    #{{
        const scalarField& T = mesh().lookupObject<volScalarField>("T").primitiveField();
        const scalarField& V = mesh().V();
        scalarField& S = eqn.source();
        const char* zn[] = {{{", ".join(f'"{z}"' for z in WINDING)}}};
        scalar Vz[{len(WINDING)}];
        for (int i = 0; i < {len(WINDING)}; i++)
        {{
            const labelList& cells = mesh().cellZones()[zn[i]];
            Vz[i] = 0;
            forAll(cells, j) Vz[i] += V[cells[j]];
            reduce(Vz[i], sumOp<scalar>());
        }}
        const scalar fV = {fills};{src}
    #}};
}}
""")
for r in regions:
    if r != "winding" and Q.get(r, 0) > 0:
        sel = "cellZone;\n    cellZone rotor" if r == "rotor" and has_zone("rotor", "rpocket") else "all"
        write(f"{case}/constant/{r}/fvModels", f"\nloss\n{{\n    type    heatSource;\n    select  {sel};\n    Q       {Q[r]:.4f};\n}}\n")
if "bearings" in regions:   # friction split front / rear over the two bearing cellZones
    write(f"{case}/constant/bearings/fvModels", "".join(
        f"\nloss_{z}\n{{\n    type    heatSource;\n    select  cellZone;\n    cellZone {z};\n    Q       {Q.get(z, 0.0):.4f};\n}}\n"
        for z in ("bearing_f", "bearing_r") if Q.get(z, 0) > 0))

# ---------------------------------------------------------------- T boundary conditions
hlist = json.load(open(HFILE)) if HFILE else {}
for r in regions:
    bc = ""
    for p in patches(r):
        m = re.match(r"(\w+)_to_(\w+)$", p)
        if m and m.group(1) == r:
            lay = LAYERS.get(frozenset((r, m.group(2))))
            extra = (f"        thicknessLayers ({lay[0]});\n        kappaLayers ({lay[1]:.5g});\n") if lay else ""
            bc += f"    {p}\n    {{\n        type coupledTemperatureNC;\n{extra}        value $internalField;\n    }}\n"
        elif p == "defaultFaces" and ADIABATIC:
            bc += f"    {p}\n    {{\n        type zeroGradient;\n    }}\n"
        elif p == "defaultFaces" and r in SKIN and p in hlist.get(r, {}):
            # per-face CFD h + radiation: mixed BC, f = (h + h_rad)/(h + h_rad + kappa/delta)
            hv = hlist[r][p]
            write(f"{case}/0/{r}/hExt", "dimensions [1 0 -3 -1 0 0 0];\ninternalField uniform 0;\nboundaryField\n{\n"
                  f"    {p}\n    {{\n        type calculated;\n        value nonuniform List<scalar> {len(hv)}("
                  + " ".join(f"{v:.4g}" for v in hv) + ");\n    }\n    \".*\"\n    {\n        type calculated;\n"
                  "        value uniform 0;\n    }\n}\n", cls="volScalarField")
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
            const scalarField& h =
                m.lookupObject<volScalarField>("hExt").boundaryField()[patch().index()];
            const scalarField Tw(*this);
            const scalar Ta = {T_AMB}, sigma = 5.670374e-8, eps = {EMISSIVITY};
            const scalarField hr(eps*sigma*(sqr(Tw) + sqr(Ta))*(Tw + Ta));
            const scalarField kd({MAT[r][2]}*patch().deltaCoeffs());
            this->refValue() = Ta;
            this->refGrad() = 0;
            this->valueFraction() = (h + hr)/(h + hr + kd);
        #}};
    }}
"""
        elif p == "defaultFaces" and r in SKIN:
            bc += (f"    {p}\n    {{\n        type externalTemperature;\n        Ta constant {T_AMB};\n"
                   f"        h uniform {H_NAT};\n        emissivity {EMISSIVITY};\n        value $internalField;\n    }}\n")
        else:      # cut faces (other regions' outer faces, e.g. bearing/shaft ends in a pocket): adiabatic
            bc += f"    {p}\n    {{\n        type zeroGradient;\n    }}\n"
    write(f"{case}/0/{r}/T", f"dimensions [0 0 0 1 0 0 0];\ninternalField uniform {T_AMB};\nboundaryField\n{{\n{bc}}}\n",
          cls="volScalarField")
print("wrote", case, "regions:", " ".join(regions))

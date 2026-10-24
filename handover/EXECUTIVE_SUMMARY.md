# Executive summary: Design9795_1 duty-cycle thermal CFD (old CAD "motor_65")

Audit date 2026-10-21. All paths are relative to `C:\Users\vibhe\Downloads\OUTPUT\` unless absolute. The machine-readable
version is `CFD/handover/ENGINEERING_BASELINE.yaml`.

## What was simulated
- **Motor**: 12-slot / 10-pole spoke-ferrite PMSM, delta winding, 52 V. Losses come from the **Design9795_1** copper design
  (GitHub repo `mishravipul361-blip/Ferrite-motor-design`, branch `spoke-v2-aluminium-and-design9795`, FEMM-Lab +
  Motor-CAD data).
- **Geometry**: the thermal geometry is the **older v7 CAD `OUTPUT/cad/motor_65`**, because no Design9795_1 CAD existed.
  Mismatch: stack 65 vs 64 mm, shaft Ø30 vs Ø25 mm. OD 160, bore 107 and rotor Ø106 match.
- **Physics**: transient all-solid conjugate conduction in OpenFOAM-12 `foamMultiRun` (solid regions).
  - Outer skin: per-face natural-convection h from a separate steady laminar buoyant external-air CFD, plus radiation.
  - End-space air: an effective conductivity (k = h_endspace × 10 mm).
  - Air gap: a Taylor-Couette thickness layer.
  - Losses: per-region volumetric sources. Copper uses (1 + 0.00393 ΔT).
- **Load points**: 5 duty points (`LOAD_POINTS.csv`). Limits: winding 155 °C, magnets 100 °C; ambient and start temperature 40 °C.

## Results (time-to-limit; 'w155' = winding max reaches 155 °C, 'm100' = magnet max reaches 100 °C)
| Point | Target | Model | First limit | Verdict | Energy balance |
|---|---|---|---|---|---|
| duty1 1782 rpm 37 N·m | 5 min | detailed | w155 at 388 s (baseline 316 s) | PASS | -0.8…+0.3 % (baseline -0.46 %) |
| duty2 2550 rpm 26.3 N·m | 15 min | baseline | w155 at 1143 s, m100 at 1166 s | PASS | -0.76 % |
| duty3 3637 rpm 20 N·m | 30 min | baseline | m100 at 1338 s, w155 at 1920 s | FAIL | -0.68 % |
| duty4 9339 rpm 3.24 N·m | 45 min | detailed | m100 at 851 s, w155 at 1300 s (baseline 800 / 1224 s) | FAIL | -1.7…-2.1 % (baseline -1.16 %) ⚠ |
| duty5 1612 rpm 12.43 N·m | 45 min | baseline | no limit by 4020 s (w 91.0 °C, m 80.7 °C) | PASS | -0.67 % |

All of these used **emissivity 0.7**, but the housing is **bare machined aluminium (ε ≈ 0.1)**, so the times are
optimistic. Only duty4 was rerun at ε 0.1 (baseline mesh): m100 at 762 s, w155 at 1098 s, balance -0.81 %.

## What worked (keep)
1. **Energy-conservation fix.** Outer-corrector residual control (OUTER_TOL 1e-3, housing 2e-2, up to 100 outer
   correctors). The adiabatic test went from -48.7 % to -0.4 %. Every run is checked with a global energy balance.
2. **gmsh conformal multi-region tet meshing**, then `gmshToFoam` and `splitMeshRegions` (`prep_base.sh`).
3. **Detailed model**: real coils re-swept from the CAD centreline. Copper parts (coil, strap, busbar, tbar) are
   merged into one `copper` region with cellZones and a single coded Joule source. Split copper regions failed the
   energy test (-1.3 %).
4. **FEMM loss segregation per load point** (stator iron 156 W at duty4, eddy share 67 %).
5. **Multi-page report site plus offline three.js 3D viewer** (`CFD/Report/Design9795_site/`).

## Main findings
- duty3 and duty4 are **magnet-limited**.
  - The rotor group takes 188 W of its own losses at duty4: bearings 109, windage 47, rotor iron 31.
  - The magnets receive about 72 W from their neighbours.
  - External rejection (housing → ambient) is the bottleneck.
- The baseline homogenised winding (isotropic k = 1 W/m·K) gives a **non-physical ~50/50 stator/air heat split**. The
  detailed model gives 69/31 at duty1. The baseline's rear end-winding hot spot is an artefact: detailed front and
  rear differ by less than 1 °C.
- Fin screening (analytical): with tapered 4→2.5 mm ring fins H16 p11.5 over the full span, UA goes from 0.94 to
  1.51 W/K at ε 0.1. **The CFD of that variant failed**: the external-air run went non-physical (U max 225 m/s), so
  no fin result exists.

## What the new CAD needs
- Rebuild all geometry-dependent artefacts: STEP import, region map, meshes, base case, external-air h map, interface
  layers, emissivity zones, slice planes and viewer export.
- Reuse the verified physics, solver controls, verification method and load points (`ENGINEERING_BASELINE.yaml`
  classes A/B).
- Use the detailed coil (or an anisotropic winding) and ε 0.1 from the start. Re-validate with the adiabatic energy
  test before any production run.

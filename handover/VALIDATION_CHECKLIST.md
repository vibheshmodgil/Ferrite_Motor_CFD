# Validation checklist (new CAD). Each gate needs PASS before moving on, with evidence recorded as a path.

## G1 Geometry
- [ ] Every STEP part imported; volumes are positive and closed. List the part → region map with volumes in cm³
      and compare to the CAD mass properties (within 2 %).
- [ ] No overlaps or interferences after fragment: gmsh fragment gives the expected volume count, with no orphans and
      no duplicate volumes.
- [ ] Simplifications are recorded with volume deltas (e.g. bobbin 4457 vs 4773 mm³ in the old CAD).
- [ ] Coordinate frame: motor axis z, gravity -y, units mm → m (transformPoints 1e-3).
- [ ] Interfaces map 1:1 to physical contacts (stator↔housing, magnets↔rotor, coil↔resin, …).

## G2 Mesh
- [ ] checkMesh reports "Mesh OK" for every region.
  - Non-orthogonality: max < 90 (warning > 70).
  - Skewness: < 4.
  - Exceptions are listed (e.g. 2 cells AR 1225 accepted for solid conduction).
- [ ] Cell count and peak RAM recorded.
- [ ] Mesh independence: **approval required.** Proposal: one point (duty4) at 2 sizes; accept if time-to-limit
      changes < 5 %. Not done in the old phase.

## G3 Physics and case
- [ ] Load points match `LOAD_POINTS.csv` exactly (rpm, torque, per-region Q, J, k_gap, k_inair, dt).
- [ ] Losses still valid for the new CAD (same stack, slots, wire?). If geometry changed EM-relevant dimensions, the
      user must approve reuse or a FEMM rerun.
- [ ] Materials and interface layers match the new CAD call-outs.
- [ ] Emissivity = 0.1 (bare Al) unless the user says otherwise; T_amb = T0 = 313.15 K.
- [ ] Winding: detailed coil (preferred) or anisotropic; not isotropic k = 1.

## G4 Verification runs
- [ ] Adiabatic energy test (ADIABATIC=1 JOULE_TC=0, 300 s): |error| ≤ 1 %.
- [ ] External-air CFD passes aircheck (U p99 ≤ 0.8 m/s) and h statistics are plausible (mean about 3–8 W/m²K).
- [ ] Internal-air CFD (if run): residuals and wall-q closure recorded; anything only 1e-3 converged is flagged approximate.

## G5 Production runs (per load point)
- [ ] Solver ended with "End"; no FPE/nan in the log.
- [ ] Global energy balance |error| ≤ 1 % (flag 1–2 %, fail > 2 %).
- [ ] Monotonic heating, with no oscillation of the max-T monitors.
- [ ] Field writes exist at the planned times (writes on the dt grid).
- [ ] Limit events extracted (m100, w155) with the other part's temperature at each event.

## G6 Post and report
- [ ] Every report number traces to a `results/**.json|txt` path.
- [ ] Charts cut at winding max 180 °C; detailed results primary where they exist.
- [ ] Old vs new comparison uses identical definitions (limits, ambient, ε, end times).
- [ ] Limitations listed: loss source, ε, bearing-loss estimate, internal-air approximations, mesh independence status.
- [ ] Site page links and assets resolve (headless check); the viewer self-test passes.

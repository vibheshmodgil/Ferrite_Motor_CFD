# MASTER PROMPT: new-CAD thermal CFD (paste into a fresh Claude Code session started in C:\Users\vibhe\Downloads\OUTPUT\CFD)

You are continuing an engineering project: a transient thermal CFD study of a 12-slot / 10-pole spoke-ferrite PMSM
(Design9795_1 losses) at 5 duty load points. The previous study used an older CAD (`OUTPUT/cad/motor_65`). Your job is
to run the same validated methodology on the **NEW motor CAD** at `<NEW_CAD_PATH>` (the user fills this in, or ask
for it once if it is missing) and to produce a comparable, traceable report.

## 0. Read first, and only this (≈ 15 kB)
1. `handover/PROJECT_STATE.md`: status, run registry, decisions, open items.
2. `handover/ENGINEERING_BASELINE.yaml`: verified settings with reuse classes (A reuse / B verify / C recompute / D do not reuse).
3. `handover/LOAD_POINTS.csv`: the 5 operating points. **Preserve these exactly**; never invent values.
4. `handover/KNOWN_ISSUES.md`: 17 failure modes with fixes. Check here before debugging anything.
5. `handover/VALIDATION_CHECKLIST.md`: gates G1–G6. Each gate must PASS, with evidence paths, before the next stage.
6. `handover/TOKEN_OPTIMIZATION_ARCHITECTURE.md`: agent roles, model routing, context and parallelism rules.

Do not rescan the whole project. Open a script only when you are about to run or change it. Do not paste whole logs:
use `tail`/`grep` and the JSON outputs.

## 1. Environment (verified)
- Windows 11, 8 logical cores, 15.8 GB RAM.
- WSL: `wsl.exe -d Ubuntu-24.04 -u cfd -- bash -lc '…'`. From Git Bash, prefix `MSYS_NO_PATHCONV=1`; the default
  distro is docker-desktop, so always pass `-d`.
- OpenFOAM-12 at `/opt/openfoam12`. Run long jobs **inside tmux only**.
- gmsh via `.venv/Scripts/python -I` (Windows) or `~/venv/bin/python` (WSL).
- FEMM 4.2 + pyfemm on Windows Python 3.10.
- Scripts are in `CFD/scripts/`. Case dirs are `~/cfd/<case>`. Results go to `CFD/results/`.
- **Only one heavy job at a time:** a solver, a gmsh build or a 3D render. Before each launch, check RAM ≥ 2 GB
  available and C: ≥ 15 GB free.
- Disable PC sleep: ask the user once.

## 2. Hard rules (user decisions)
- **Same load points and limits.** Winding 155 °C, magnets 100 °C; T_amb = T0 = 40 °C. Charts cut at winding 180 °C.
  Mark both events (m100 with the winding T at that moment; w155 with the magnet T).
- **Bare machined aluminium housing:** emissivity **0.1** (env `EMISSIVITY=0.1`). Use fin-envelope emissivity
  scaling (`fin_eps.py`). Natural convection only, horizontal shaft, gravity -y, axis z.
- **Use the DETAILED winding model** (real coils; copper parts merged into one `copper` region with cellZones,
  MERGE_CU=1) as the primary model. Do not use the isotropic k = 1 homogenised winding: it gives a non-physical
  stator/air split.
- **Envelope and fins:** max OD 205 mm (glands may protrude). Fins tapered 4 mm base / 2.5 mm tip. Fin variants are run
  on this new CAD; analytical screen first (`fin_screen.py`), then CFD on the shortlist.
- **Reporting:**
  - Multi-page site (`make_report_duty.py --site`, with tabs per page) plus the 3D viewer (`export_viewer.py`).
  - Detailed results are primary wherever they exist.
  - Every number traces to a results file.
- Losses come from `loadpoints.json` (Design9795_1). If the new CAD changes stack, slot or wire geometry, **stop and
  ask** whether to rerun FEMM (`femm_duty_*.py`) or reuse the losses.

## 3. Workflow (stop at each gate; update PROJECT_STATE.md at each ✔)
1. **CAD inventory** (G1).
   - List the files and formats, and map parts to regions: housing, cover, stator, coil, bobbin, resin, busbar,
     strap, tbar, rotor, magnets, shaft, bearings, end-space air.
   - Compare against the old CAD: OD, bore, stack, shaft, end space, fins.
   - Report geometry changes that affect the mesh, patches, physics or extraction.
2. **Geometry and mesh** (G1, G2).
   - Adapt `build_mesh_detailed.py` (and `build_mesh.py --air-only` for the external air) to the new STEP names.
     Never reuse old meshes, patch names, region volumes, h maps, slice planes or decomposition.
   - Apply the KNOWN_ISSUES fixes proactively:
     - re-sweep the coils from their centreline;
     - single fragment;
     - save the BREP;
     - Delaunay 3D;
     - NTHREADS=1;
     - an 8 GB RSS kill switch.
   - Then run checkMesh.
3. **Base case:** `MERGE_CU=1 bash scripts/prep_base.sh <msh> ~/cfd/base_new`.
4. **External-air CFD** (`air_case.sh`, steady laminar buoyant) on the new housing.
   - It must pass `aircheck.sh`. The last fin variant failed this with U max 225 m/s; if it fails, try lower
     relaxation or pseudo-transient and check mesh quality at the fin tips.
   - Then `map_h.py` → `h_new.json` and the `fin_eps.py` envelope emissivity.
5. **Adiabatic energy test** (`energy_test.sh`, BASE=~/cfd/base_new): |error| ≤ 1 %, or do not continue.
6. **Short validation run:** duty1 to 60 s. Check the "End" line and the energy balance.
7. **Production runs**, one at a time, in their own case dirs:
   - **Order:** duty4 first (the critical point), then duty3, duty1, duty2, duty5.
   - **End times:** max(target, 1.5 × time to the winding 155 °C limit), on the write grid. Writes are multiples of
     dt; use about 10–15 field writes per run, for the viewer and animations.
   - **Post-processing:** slices, heatflow, export3d and energy_balance (G5).
8. **Internal-air CFD** (optional, `inair_cfd.sh`) at the duty1 and duty4 speeds. The duty4 speed needs upwind and
   low URF.
9. **Fin study on the new housing:** screen, then CFD for the top 3 at duty4.
10. **Post and report** (G6).
    - Compare with the old-CAD results (`results/duty*`, `results/detailed`) using identical definitions.
    - Note that the old runs used ε 0.7, except `results/duty4_eps01`.
    - Rebuild the site, the single report and the viewer.
11. **Handover:** update `handover/PROJECT_STATE.md` (run registry, open items) and `LOAD_POINTS.csv` status.

## 4. Agents and tokens
- **Main session (you)** orchestrates and owns `handover/` plus memory. Spawn at most 3 background agents:
  - **GEO** (opus): steps 1–5;
  - **RUN** (sonnet): steps 6–8;
  - **REPORT** (sonnet; haiku for audits): step 10.
- Agents report in **5 lines or fewer** (numbers, paths, blockers) and wait with one background waiter instead of
  polling.
- Only run independent work in parallel. Never run two solvers or meshers at once, and never write the same case dir
  from two agents.
- Keep replies to the user short. Ask the user only for genuine decisions: loss reuse, material or finish, envelope,
  approval of acceptance limits.

## 5. Acceptance (from VALIDATION_CHECKLIST.md)
- checkMesh OK.
- Adiabatic test within 1 %.
- Per-run energy balance within 1 % (flag 1–2 %, fail above 2 %).
- Air CFD passes aircheck.
- Solver "End", no FPE.
- Limit events extracted.
- Every report number traceable.
- Mesh independence (one point, two sizes, < 5 % change in time-to-limit) is **approval-required**: propose it to
  the user.

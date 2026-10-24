# U666 benchmark CFD: knowledge note (updated 2026-10-23 12:20)

Read this note first. Detailed history is in `results/u666/steps_log.md`. The mesh-specific state is in `handover/u666_mesh_handoff.md`, written by the outgoing MESH agent.

## Goal
- Thermal CHT (OpenFOAM 12) of the U666 benchmark motor, which has test data, at 5 duty points with the U666 Motor-CAD losses.
- Then calibrate against the test (data pending from the user) and apply the method to our motor.
- Limits: winding 155 °C, magnets 100 °C. Target durations: duty1–5 = 5/15/30/45/45 min.

## Machine rules (hard)
- 4-core laptop, 15.8 GB RAM. Run ONE heavy job at a time; never run gmsh and OpenFOAM together. Keep ≥20 GB free on C:.
- Launch heavy jobs DETACHED (PowerShell Start-Process, or WSL tmux). Claude Code background shells get killed by the memory reaper.
- gmsh: Windows venv `CFD/.venv` (gmsh 4.15.2, OCC). OpenFOAM 12: WSL Ubuntu-24.04, user `cfd`, cases in `~/cfd/`.
- Agents report only at milestones, in 5 lines or fewer. Do not paste logs; use tail/grep.

## Inputs
- CAD: `U666 CAD/U666_L4_20261022/ge250440_step.stp` (Creo, 599 solids). STEP import takes 18 min, so always start from the BREP cache `mesh/u666/u666.brep`. Inventory: `mesh/u666/inv.json`. Motor axis is z.
- Losses: `loadpoints_u666.json` (DC Cu, AC Cu, iron, magnet, windage, friction per point; totals 1201/651/487/716/175 W).
- Winding: `results/u666/winding_props.json`.
  - Kf 0.555, 5 strands of Cu 0.71 / 0.76 mm, 120 conductors per slot, liner 0.25 mm, no potting.
  - k_T 1.12, k_ax 217, rho 5510, cp 473. Liner modelled as a contact R of 1.67e-3 m²K/W.
  - End winding k (r, θ, z) = (1.05, 205, 205).

## Materials (differences from the old ferrite run)
- NdFeB magnets; brass rotor end caps; no busbar.
- Housing is cast Al, machined, bare, ε 0.1.
- All other materials as in `handover/ENGINEERING_BASELINE.yaml`.

## Geometry chain (scripts/)
1. `u666_subset.py`: u666.brep → `mesh/u666/subset.brep`. Keeps thermal parts only, using OCCExportOnlyVisible (49 s).
2. `u666_geo.py`: subset → `u666_geo_raw.brep` / `u666_geo.brep` + `.json`. Log: `mesh/u666/geo.log`, about 6–25 min.
   - Stator and rotor stacks are ONE lamination profile extruded over the stack length (user method). Do not fuse laminations.
   - Magnets become 18 extruded columns. Wedges are merged into the slot opening.
   - The slot winding fills the liner space (CAD slot 101.65 mm² vs Motor-CAD 96.67 mm²; rho, Cu and k scaled).
   - End windings are about 5 mm shells at r 55.5 with about 30 mm overhang (CALIBRATION KNOB).
   - Inner air (`inair`) is a cavity envelope of 3 cylinders. Its contact with the outer air is 0 mm² (leak fixed). Volume closure is exact (360000 cm³).
   - Regions: air, inair, housing, stator, slot, endw, rotor, rpocket, magnets, endcaps, shaft, bearings, seal, wedge.
3. `u666_fuse.py` (optional): fuses the pieces of each region. NEVER fuse the housing (OCC fails or loses 370 cm³). Leaves dangling faces, so it is currently skipped.
4. `u666_mesh.py --solids` / `--air`: gmsh Delaunay, H 2.5. Log: `mesh/u666/mesh_solids.log` / `.err`.
5. `u666_prep_base.sh` builds `~/cfd/u666_base` from the mesh. `u666_make_case.py` writes materials, losses, contacts and BCs; env knobs: IRON_STATOR_FRAC 0.8, BRG_FRONT_FRAC 0.5, T_REF_C 100.
6. `u666_energy_test.sh` + `u666_energy_balance.py`: an adiabatic run must close within ±1.5 %.
7. `u666_air_case.sh` + `u666_aircheck.sh`: external natural-convection air gives the h map. Gate: U max ≤ 5 m/s. Ambient 40 °C, gravity -y, horizontal shaft.
8. Duty runs duty1–5, one at a time, then post-processing and the report.

Scripts 5–8 are written but NOT yet run.

## Mesh status (12:20, 23 Oct)
- Repeated gmsh failures from dirty CAD faces: tori and spheres under 0.05 mm², fin B-splines, slivers at the terminal-box gasket rim (z -85), and circles 0.07 mm apart at the rear end of the shaft/rotor.
- Errors seen: "1D mesh not a closed loop", "PLC segment-facet intersect", overlapping facets.
- Full list with fixes: steps_log S7.

## DECIDED approach for the clean-up (user 12:15): defeature once, per part, BEFORE the fragment step
- First, inventory each part: fillet, chamfer, hole and thread faces, with radius and area. Write it to `results/u666/defeature_inventory.md` for the report.
- Remove in each part (gmsh `occ.defeature`, ONE part at a time, small face lists, never one huge call):
  - fillets and rounds under 2 mm radius;
  - chamfers under 2 mm;
  - holes under 3 mm, and threads;
  - text and logos.
- KEEP exact: stator–housing fit, bearing seats, slots and teeth, air gap, magnet pockets, the main outer skin and fins (fin-root fillets 2 mm or larger stay).
- If a part fails to defeature, replace it with a primitive of the same volume and contact footprint, and log it. Candidates: gasket, terminal cap, terminal cover.
- Log removed area and volume per part. Thermal effect expected under 0.5 °C. Also expect fewer cells and faster runs.

## Open questions for the user (do not block on them; use the placeholders)
- Iron loss split stator/rotor (placeholder 0.8/0.2).
- DC copper reference temperature (placeholder 100 °C).
- duty4 friction of 251 W: real?
- Test data: T(t) per sensor, sensor locations, ambient, mounting, airflow.

## Reporting
- Every step goes into `results/u666/steps_log.md` (S0–S11): what was done, assumptions, problems and fixes.
- Main agent: runs `scripts/u666_method_report.py` → `Report/U666_method.html` and publishes it.

## Status update (2026-10-23 17:00) — this supersedes "Mesh status" above
- Real housing CAD: gmsh, per-face defeature and snappy (closed STLs overlap → 1007 zones) all FAILED. Do not retry them.
- ACTIVE route: simplified housing `mesh/u666/housing_simple.brep` (scripts/u666_housing_simple.py; volume −2 %, fin area +1 %, fit and seats exact; knob dict K). Enabled with `U666_HOUSING=simple` in u666_geo.py; the CAD version is kept in scripts/u666_geo.py.bak_cad.
- If a PLC error comes back: cut the endcaps by the shaft before the fragment (circles 0.07 mm apart at z −2.2, r 15).
- Next: mesh OK → handoff/u666_base_handoff.md → fresh agent for prep_base and the energy test.

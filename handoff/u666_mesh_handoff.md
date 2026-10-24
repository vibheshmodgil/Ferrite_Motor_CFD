# U666 solids mesh: handoff (MESH agent, 2026-10-23 12:25)

## File chain (Windows python: `.venv\Scripts\python -I`, gmsh 4.15.2, 1 thread)
1. `scripts/u666_subset.py` -> `mesh/u666/subset.brep/.json` (needed CAD solids only; not rerun).
2. `scripts/u666_geo.py` -> `mesh/u666/u666_geo.brep` + `.brep.json` (region -> volume tags), `results/u666/geo.json`, log `mesh/u666/geo.log` (~25 min).
3. Copy `u666_geo.brep(.json)` -> `u666_geo_raw.brep(.json)`. This copy is the input of the optional step 4.
4. (optional, NOT in the current chain) `scripts/u666_fuse.py`: fuses each region's pieces and re-fragments (~25 min) -> overwrites `u666_geo.brep`. Housing fuse fails in OCC, and the one-by-one fallback lost 370 cm3: never fuse the housing (FUSE_SKIP default `air,endcaps,housing`). Fusing the endcaps left a dangling face. Fusing the shaft fixed its crossing circles.
5. `scripts/u666_mesh.py --solids` -> `mesh/u666/u666_solids.msh` + `_regions.json`, log `mesh/u666/mesh_solids.log/.err`.
6. Then (untested): WSL `bash scripts/u666_prep_base.sh <msh> ~/cfd/u666_base` (also merges the seal into the wedge zone), then `u666_energy_test.sh`.
- Chain script: `<scratchpad>\geofuse.cmd` (geo -> copy raw -> mesh). Launch it detached:
  `Start-Process -WindowStyle Hidden cmd.exe -ArgumentList "/c","<path>\geofuse.cmd"`; set `$env:ALG3D="1"` first. When it finishes it writes `mesh/u666/chain.done`.
- **RUNNING NOW (started 12:11)**: the chain with the new cap fallback (geo, then mesh). Check `geo.log` (leak line, closure), then `mesh_solids.log` (`tets:` = success).

## What works
- Leak: inair-air contact 0.0 mm2, volume closure exact (geo.log). Fixes are in S4 of steps_log.md: outside envelope pieces -> air; seal = own region (polymer); open shaft bore -> air; hex hole plug in the cap.
- rpocket rule: 8 pieces, 48.6 cm3, still air.
- Region volumes (cm3, 09:43 run): air 356180, shaft 89.38, bearings 32.16, inair 1402.7, housing 1109.8, seal 2.88, stator 477.33, endw 107.97, slot 221.58, endcaps 36.77, wedge 9.52, rpocket 48.55, rotor 244.84, magnets 36.55. The housing changes by ~-0 to +1 cm3 with the cap fallback (lid thickened to keep 53.3 cm3).
- 2D meshing now passes everywhere except at the terminal-box cap/gasket rim.

## Failures so far (all at H 2.5, Delaunay 3D)
| # | Error | Face / location | Fix applied |
|---|---|---|---|
| 1 | 2D closed loop | torus 0.2 mm2, gasket rim x -52 y -45 z -85 | gasket shrunk (superseded by #8) |
| 2 | 2D hang | housing B-spline lug face 1428, x -90 y 24 z -5 (crossing curves 3343/3345) | MeshSizeFromCurvature 0 (env CURV) |
| 3 | 3D overlapping facets | box envelope cylinder r 72.61 vs cone on the box outside | envelope cut by the housing, interior piece kept |
| 4 | 3D overlapping facets | rotor gap annulus r 42.68 vs lamination OD dips 42.70-42.88 | annulus r 42.6 fused with the lamination |
| 5 | 3D PLC "segment and facet intersect" (no location) | 1D crossings of circles 0.07 mm apart at the shaft/rotor rear end, z -2.2 r 15; invalid triangles on fin B-splines (every 66 surfaces, x -56 y -60, 10 mm pitch) and cap torus (z -97) | shaft fused (u666_fuse); invalid-triangle surfaces re-meshed with MeshAdapt + finer size (works); proximity sizing tried (1.7 M nodes, off: PROX=0) |
| 6 | 3D overlapping facets, 0.065 deg | housing-housing slivers 0.18 mm2 at the gasket band z -86.7..-85.2 | FACET_TOL 0.01, then PLC remained |
| 7 | 2D closed loop / inverted faces | gasket+cap+cover fused: inverted torus (-0.0018 mm2) and cones (-1404, -32 mm2) at x -55..-30 y -52..-35 z -86..-41 | mesh.py defeatures skin faces / fuses same-region pairs on failure; heal failed (stale tag) |
| 8 | (running) | - | FALLBACK: cap 114 + gasket 74 replaced by extruded profiles (walls = section z -88 over -90.5..-83.5; lid = section z -91.5 over CAP_LID_Z0 -93.55..-90.5), fused with cover 64. Isolated test: 0 tiny faces |

## Open fixes / next steps
- If #8 meshes: run checkMesh via prep_base. Log cells per region, max non-orthogonality and skewness in S7. Then the energy test (S8).
- If PLC is back: the shaft circles (#5). Fuse the shaft locally in geo.py (the shaft vs endcap/rotor overlap: cut the endcaps by the shaft before the fragment), or run u666_fuse.py with FUSE_SKIP=air,endcaps,housing.
- mesh.py contains retry logic: compound/defeature/fuse on a 2D failure, then an invalid-triangle re-mesh. The defeature branch uses `regions` tags. A heal fallback is in, but it errored on a stale tag.
- Air mesh (`--air`) is untested. BOX now spans all air pieces. Curvature sizing is off for the air too.
- Knobs: GASKET/CAP_LID_Z0, CURV, PROX, FACET_TOL, ALG3D, VERB, FUSE_SKIP.

## Commands
```
cd C:\Users\vibhe\Downloads\OUTPUT\CFD
.venv\Scripts\python -I scripts\u666_geo.py   > mesh\u666\geo.log 2> mesh\u666\geo.err
copy /y mesh\u666\u666_geo.brep mesh\u666\u666_geo_raw.brep & copy /y mesh\u666\u666_geo.brep.json mesh\u666\u666_geo_raw.brep.json
set ALG3D=1 & .venv\Scripts\python -I scripts\u666_mesh.py --solids > mesh\u666\mesh_solids.log 2> mesh\u666\mesh_solids.err
wsl.exe -d Ubuntu-24.04 -u cfd bash -lc "bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/u666_prep_base.sh /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/mesh/u666/u666_solids.msh ~/cfd/u666_base"
```

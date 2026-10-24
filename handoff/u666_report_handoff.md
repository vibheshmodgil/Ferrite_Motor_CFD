# REPORT3 handoff (2026-10-24)
Build: `.venv\Scripts\python -I scripts/u666_site.py` (BelowNormal, single thread; log results/u666/report/site_build.log, errors site_err.log). Site: Report/U666_site/*.html. Local only.
Rerun any time: duty3-5 appear automatically when postProcessing exists (case = ~/cfd/u666_<duty>, override in results/u666/report/sources.json). Everything is cached: plane data in results/u666/report/cache/*.npz (incremental per saved time), PNG/MP4 skip when `<file>.key` (last data time + scripts/u666_figs.py mtime) matches, WSL render steps skip when output file exists (delete the file to force).

## New pieces
- scripts/u666_figs.py: reads VTK cut planes straight from the WSL share; contour_fig (2x2 planes, shared colour bar, limit marks + hatched cells over limit), anim_temp (axial + mid-stack, 12 s mp4), anim_budget (stored energy per region from Tintz/Tint x rhocv in case_props.json vs injected = Q dict with copper T feedback, ambient outflow Qout_*; closure residual printed as an observation), observations (auto, 3-5 per duty; extra text from results/u666/report/observations_<duty>.md, one bullet per line, is appended).
- scripts/u666_report_render.py + .sh `extra` step (WSL python3+vtk, nice 19): regions_{radial,axial}.png (per-region mesh), housing_overlay.png (CAD STL cut vs simplified), air_U/air_T.png (needs ~/cfd/u666_air/450 -> foamToVTK in ~/rep/air), h_3d.png, h_unwrapped.png, hmap_stats.json.
- scripts/u666_slicefix.sh <case>: re-cuts the radial planes from the saved T fields (reconstructPar -fields T, foamPostProcess), nice 19. Run in tmux (nohup via `wsl bash -c '&'` dies when wsl returns). Done for duty1, duty2.

## FINDING (affects data)
u666_make_case.py wrote the radial cut planes with z in mm on a metre mesh -> radial_stack / ew_front / ew_rear vtk are EMPTY in duty1-3 (axial fine). Fixed in make_case (point *1e-3) so duty4/5 write them at 10 s. duty3 is running with the bug: when it is finished run `tmux new -d -s rep 'bash scripts/u666_slicefix.sh ~/cfd/u666_duty3'` (radial planes then every 30 s). Radial/end-winding frames start from a synthetic uniform 40 C at t=0.

## Not done / open
- 3D animation of the full fields: skipped (needs reconstructed fields for all times and a 3D renderer, too heavy next to the OpenFOAM job). 3D viewer page still Pending (see old plan: export_viewer-based u666_export_viewer.py).
- Heat-flow network animation (animate_heat.py) not ported: replaced by the energy-budget mp4 (no per-interface flows are in the duty output other than Qif_*).
- Observations are auto text; no hand-written commentary yet.
- Calibration page still waits for test data.

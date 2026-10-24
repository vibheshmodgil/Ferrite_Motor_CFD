# U666 base case (BASE3, 2026-10-24): ENERGY GATE MET (-1.14 % at 60 s), next: air h map, then duty1
Details: results/u666/steps_log.md S8c (fix, assumptions, pair sums) and S8b (prism route).

## State
- Base `~/cfd/u666_base_nc`: 1.446 M cells. Prisms (z-extruded) for winding, stator, rotor, magnets and wedge; tets for the rest. Test case `~/cfd/u666_e2`.
- Mesh: `scripts/u666_mesh.py --solids --group G` (env EXTRUDE, DZ 2.5, SNAPZ 0.5, BOOLTOL 0.03, ALG2D 6). Labels come from the tet meshes in `mesh/u666/tet_bak/` (keep them!).
- Tooth-tip fix (env TIP, default on):
  - The wedge inner arc is cut at the exact tip radius, 43.535.
  - The rotor arc is split at the 72 tip angles.
  - New pair: rotor_to_stator / stator_to_rotor.
  - The pre-fix meshes are in `mesh/u666/prism_s8b/`.
- Remesh: `scripts/_s8c_mesh.bat` (env S8C="wedge stator rotor"), launched detached with PowerShell Start-Process. Each group takes ~3-5 min.
- Run: `scripts/_s8c_run.sh` → `_e2.sh` (env ASM=1 re-assembles + checkMesh + interface areas, then DT, N, END).
  - Launch: `wsl -d Ubuntu-24.04 -u cfd -- tmux new-session -d -s e2 "bash /mnt/c/.../scripts/_s8c_run.sh"`.
  - Done when log.e2 has "EXIT".
  - Then `_s.sh` (balance + pair sums) and `_r.py` (per-region rate residuals).
- Plot: `.venv/Scripts/python -I scripts/u666_plot_balance.py <energy_ts.csv> <out.png> "title"`.

## Results (adiabatic duty1, dt 1 s, nOuter 3, anisotropic winding + stator)
- Balance: -1.05 % at 5 s, -1.14 % at 60 s (plateau). Before the fix: -8.7 %.
- Stator residual: -0.7 W (was -109 W).
- Pairs are fine except:
  - wedge|winding: -1.85 W of 25 W (7 %).
  - inair|winding: -1.1 W of 104 W (1.06 %).
  - Sub-watt pairs with 0.3-0.6 W sums.
  - The winding internal residual is -7 W.
  - Every winding pair loses on the winding side, so the likely cause is the anisotropic-winding flux evaluation (same signature the stator had).
  - This is OPEN but within the gate. Optional check: WIND_ISO=1 and compare.
- checkMesh: all regions OK except inair skew 9.2 (tet, unchanged).
- Timing: 5.9 s wall per s simulated incl. ~80 s setup (4.5 excl.). A duty1 run of 300 s costs ~25 min; 45 min duty runs are ~3.5 h each.

## Next
1. External air h map: `u666_air_case.sh` + `u666_aircheck.sh`. Gate U max ≤ 5 m/s, ambient 40 °C, gravity -y.
2. duty1: `u666_make_case.py <base> <case> duty1` without ADIABATIC; it handles the loadpoints_u666.json keys.
   - Use dt 1, N 3 (validated).
   - Write the time series for the report animations.
3. Open input placeholders: iron split 0.8/0.2, T_REF 100 °C (see U666_NOTE).

## WSL gotchas
- Export `MSYS_NO_PATHCONV=1`.
- Inline `bash -c` with $vars or $() gets mangled from Git Bash. Use script files.
- Never `pkill -f foamMultiRun`.
- A tmux session named e2 may already exist after a WSL restart; check `tmux ls` first.
- Heredoc-python "\n" turns into real newlines; use the Edit tool.
- The fragment of a single section now returns no map; this is handled in u666_mesh.py.

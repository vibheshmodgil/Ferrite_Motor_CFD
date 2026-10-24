# Known issues and verified fixes (keep; check before debugging)

| # | Symptom | Root cause | Verified fix |
|---|---|---|---|
| 1 | Solid run lost 49 % of heat | foamMultiRun lagged region coupling with 1–2 outer correctors | outerCorrectorResidualControl e 1e-3 (housing 2e-2), up to 100 outer correctors; adiabatic test -0.4 % |
| 2 | Detailed energy test -1.3 %, every step hits the 100-iteration cap | Segregated coupling between small copper parts (strap residual stalls ~0.1) | Merge coil/strap/busbar/tbar into one `copper` region with cellZones (MERGE_CU=1), one coded Joule source → -0.9 % |
| 3 | Anisotropic winding k diverged | Per-coil frames on a tet mesh | Use the detailed coil; isotropic k = 1 gives a wrong stator/air split |
| 4 | gmsh stalls on the coil | STEP coil is one 2 m B-spline face, turns 0.1 mm apart | Re-sweep from the CAD centreline in 5 mm segments (bare 2.9 mm Cu) |
| 5 | CAD bobbins won't mesh | Float 0.10–0.25 mm off the tooth; overlapping micro-faces | Simplified bobbin built from the tooth (CAD wall 1.45 mm); volume 4457 vs 4773 mm³ |
| 6 | "duplicate volume" in 3D meshing | HXT-specific | Delaunay 3D from the saved BREP (`--from-brep`) |
| 7 | C: filled to 0 bytes; WSL `getpwnam failed 5` | Per-step function-object field writes, plus pagefile growth | `objects ();` on monitors; watch disk; sparse vhdx + fstrim; `wsl --shutdown` |
| 8 | Background jobs killed ("low memory") | Claude Code reaps idle background shells under RAM pressure | One heavy job at a time; gmsh only when WSL is idle; optionally start Claude Code with CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1 |
| 9 | Run paused about 5.5 h | PC slept | Disable Windows sleep (the session keep-awake gets reaped) |
| 10 | Empty slice folders | Write/post times not on the dt grid | Writes and endTime must be multiples of dt |
| 11 | inair duty4 diverged (FPE) | 9339 rpm with 2nd-order defaults | Upwind U, URF p_rgh 0.15 / others 0.3 (env URF_P, URF, DIVU in inair_cfd.sh) |
| 12 | Fin variant air CFD non-physical (U max 225 m/s) | Unresolved (new fin mesh; laminar steady buoyant) | **OPEN.** Check the air mesh quality near the fin tips, use pseudo-transient or lower URF, and keep the aircheck gate |
| 13 | `pkill -f foamMultiRun` killed its own shell | The pattern matched its own bash -lc command line | Use `pgrep -x` or kill by tmux session |
| 14 | `rm -rf` of old cases blocked | Claude Code auto-mode classifier (irreversible delete) | The user runs the delete themselves |
| 15 | Emissivity 0.7 used on bare Al | Default carried from the old project | EMISSIVITY=0.1 for the new CAD |
| 16 | Usage/rate limits stop agents | Account session/weekly limits | Agents resume with SendMessage; keep reports ≤ 5 lines |
| 17 | WSL default distro errors (no bash) | Default distro = docker-desktop | `wsl.exe -d Ubuntu-24.04 -u cfd`; MSYS_NO_PATHCONV=1 from Git Bash |

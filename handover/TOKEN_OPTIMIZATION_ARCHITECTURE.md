# Agent architecture, memory and token plan (for the new-CAD phase)

## Platform facts (verified in this session)
- **Claude Code agents.** Claude Code runs background subagents through the `Agent` tool. Each one can take a `model`
  override (`haiku`, `sonnet`, `opus`), resumes with `SendMessage`, and reports through a hand-back message.
  - Model choice is **manual per spawn**; there is no automatic model switching.
  - Subagents share the account's usage limits. Rate limits stopped agents many times.
- **Measured subagent usage (old phase).** The values come from task notifications:

  | Agent | Tokens |
  |---|---|
  | VISUALS (report) | ~337k |
  | DETAIL (geometry and mesh) | ~333k |
  | CFD | ~230k |
  | FEMM | ~71k |

  - The main-session total was not measured.
  - Without a measured baseline, no saving is promised.
- **Hardware.** 8 logical cores, 15.8 GB RAM (WSL VM 9.9 GB). Only **one heavy job** can run at a time:
  - an OpenFOAM run (3–4 ranks);
  - a gmsh build (2–6 GB);
  - a pvpython render.
  - Light jobs (python post-processing, report building, file reads) can run in parallel with one heavy job.
- **Background shells get reaped.** Claude Code kills idle background shells under RAM pressure, which ended several
  monitors. Prefer tmux in WSL for long jobs, plus one short `until … ; do sleep 600; done` waiter per job.

## Logical roles mapped to real agents (keep to 3 live agents at most)
| Role | Who | Model | Owns |
|---|---|---|---|
| 1 Orchestrator, 2 Memory, 3 Router | **Main session** | the user's session model | task list, approvals, `handover/*.md`, `memory/` |
| 4 Geometry & Mesh, 5 Physics/Case | **GEO agent** (one agent, sequential) | opus (CAD and boolean debugging is hard) | STEP import, region map, meshes, base cases, h map, energy test |
| 6 Solver & Convergence | **RUN agent** | sonnet | tmux queues, run_case / det_run, balances, post (slices, heatflow, export3d) |
| 7 Post/Validation, 8 Report/Audit | **REPORT agent** | sonnet; haiku for asset checks and size audits | make_report_duty.py (--site), viewer export, audit tables against results/*.json |

Use opus subagents only for physics interpretation, solver divergence and geometry/boolean failures. Use haiku for
log tails, file inventories, "is X done" checks and CSV/JSON extraction.

## Context rules (cheap by default)
1. **Session start.** Read `handover/PROJECT_STATE.md` and `ENGINEERING_BASELINE.yaml` first. Read nothing else until
   a task needs it.
2. **Logs.** Never paste whole logs. Use `tail -n 5`, `grep -E "FATAL|nan|Floating|End$|Time = "`, or energy_balance.json.
3. **Reports.** Agents report in 5 lines or fewer: numbers, paths, blockers. The orchestrator does not restate tables
   it has already given.
4. **Facts.** Each verified fact lives in exactly one place:
   - numbers in `results/*.json`;
   - settings in the YAML;
   - status in PROJECT_STATE.md.
   Cite these by path; don't copy them around.
5. **Updates.** Update PROJECT_STATE.md at milestones only: mesh OK, energy test, each run done, report rebuilt.
6. **Cache invalidation.** If a script or mesh changes, re-run the gate it feeds (checkMesh, energy test) before
   reusing old numbers.
7. **Waiting.** Don't poll. Arm one waiter per job (tmux has-session loop, or a grep for "post done|FAILED").

## Parallelisation rules
- Only one solver or mesher at a time. Every load point gets its own case directory (`~/cfd/<prefix><lp>`), so runs
  never share an output directory.
- Run in parallel only: report building, analytical screens, FEMM (Windows) while WSL is idle, and doc and log
  inspection.
- Before each heavy launch, check:
  - Windows available RAM ≥ 2 GB;
  - C: free ≥ 15 GB;
  - no other foam or gmsh process running.
- Never `pkill -f` with a pattern that can match the calling shell.

## Memory files (no duplicates)
- `handover/PROJECT_STATE.md`: phase, run registry, open items, decisions, approvals.
- `handover/ENGINEERING_BASELINE.yaml`: settings and their provenance, with reuse classes.
- `handover/LOAD_POINTS.csv`: the operating points.
- `handover/KNOWN_ISSUES.md`: failure modes and fixes.
- `handover/VALIDATION_CHECKLIST.md`: the acceptance gates.
- `~/.claude/projects/.../memory/*.md`: Claude Code auto-memory (preferences and pointers only; it points to the
  handover files rather than copying them).

# Autolab Day-1 Checklist

Use this when turning the scaffold into a live rig.

## Rig Setup

1. Create or select the `autolab` rig.
2. Install the directives:
   - `directives/crew.md`
   - `directives/polecat.md`
3. Install the formula overlay:
   - `formula-overlays/mol-polecat-work.toml`
4. Decide who is the planner:
   - one crew worker or the Mayor
5. Set scheduler capacity to validated comparable-runner count, not terminal count.

## Research Discipline

1. Define the bead label vocabulary from `taxonomy.md`.
2. Create one convoy for the initial research theme.
3. Use one planner and one worker first.
4. Do not add more workers until duplicate-prevention is actually working.

## Live Autolab Setup

1. Verify a comparable benchmark runner is available:
   - local path: `nvidia-smi` exists, reports an NVIDIA H100, and the checked-in wrapper prerequisites are present
   - managed path: use only a runner that has already produced trusted comparable benchmark results
2. If no comparable runner exists, stop here and wait. Do not dispatch local benchmark beads.
3. Register or load autolab credentials.
4. Create the local autolab contributor workspace.
5. Fetch the current master and full experiment DAG.
6. Read the research history before running any experiment.
7. Dispatch only one fresh hypothesis per comparable runner slot.

## First Success Criteria

You are ready to scale beyond one worker only when:

- experiment beads are consistently well-formed
- recent failures are being recorded clearly
- duplicate experiments are being avoided
- the planner is reacting to new master changes quickly

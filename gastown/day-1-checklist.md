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
5. Optionally add one dedicated literature scout:
   - `gt crew add researcher --rig autolab`
6. Set scheduler capacity to the number of concurrent HF Jobs you are willing
   to pay for.

## Research Discipline

1. Define the bead label vocabulary from `taxonomy.md`.
2. Create one convoy for the initial research theme.
3. Use one planner and one worker first.
4. Add `researcher` only after the planner is actually preventing duplicates.
5. Do not add more benchmark workers until duplicate-prevention is actually
   working.

## Live Autolab Setup

1. Register or load autolab credentials.
2. Authenticate to Hugging Face and set `AUTOLAB_HF_BUCKET`.
3. Create the shared HF bucket once and run the `prepare` bootstrap job.
4. Choose the default HF Jobs flavor and timeout for experiment runs.
5. Fetch the current master and full experiment DAG.
6. Read the research history before running any experiment.
7. Dispatch only one fresh hypothesis per paid job slot.

If you use a local fallback instead of HF Jobs, treat it as valid only when the
host is already a trusted comparable runner.

## First Success Criteria

You are ready to scale beyond one worker only when:

- experiment beads are consistently well-formed
- recent failures are being recorded clearly
- duplicate experiments are being avoided
- the planner is reacting to new master changes quickly

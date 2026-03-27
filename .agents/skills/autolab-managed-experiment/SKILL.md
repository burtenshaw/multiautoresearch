---
name: autolab-managed-experiment
description: "Run one Autolab benchmark experiment safely on Hugging Face Jobs. Use when a polecat or planner is preparing, auditing, launching, or reviewing a single train.py hypothesis against current hub master."
---

Use this for any single Autolab experiment bead that should result in exactly
one managed benchmark run.

## Workflow

1. Load credentials and refresh from the hub:
   - `. ~/.autolab/credentials`
   - `python3 scripts/refresh_master.py --fetch-dag`
2. Edit only `train.py` for the single intended hypothesis.
3. Run preflight before launch:
   - `python3 scripts/hf_job.py preflight`
4. Launch exactly one managed experiment:
   - `python3 scripts/hf_job.py launch --mode experiment`
5. Stream logs and parse the final metric:
   - `python3 scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log`
   - `python3 scripts/parse_metric.py /tmp/autolab-run.log`
6. Record the bead note or notebook entry with the hypothesis, job id, and
   final metric.
7. Submit only if `val_bpb` beats current hub master.

## Guardrails

- Treat `train_orig.py` as the refreshed hub-master base. If preflight reports
  multiple known hypothesis categories, stop and inspect the diff before
  launching.
- Never run `python3 scripts/hf_job.py launch --mode prepare` from a bead
  worktree. `prepare` is rig-wide bootstrap work, not per-experiment work.
- Do not launch a second experiment job for the same bead unless you have a
  specific reason and intentionally override the duplicate check.
- If the workspace looks stale against live hub master, stop and rewrite the
  bead rather than rationalizing the mismatch.

## Fast Checks

- `python3 scripts/hf_job.py preflight --json`
  Use this when you need to inspect the diff preview, active conflicts, or
  detected change categories programmatically.
- `bd show --long --id <BEAD_ID>`
  Use this to confirm the bead still describes the same single-change
  hypothesis you are about to run.

---
name: autolab-reporter
description: "Operate the local Trackio reporter for Autolab HF Jobs. Use when a reporter or planner needs to inspect scores, active jobs, worker anomalies, duplicate launches, or the overall experiment board."
---

Use this for the control-plane view of the experiment fleet.

## Workflow

1. Load credentials:
   - `. ~/.autolab/credentials`
2. Sync the latest HF Jobs into Trackio:
   - `uv run scripts/trackio_reporter.py sync --project autolab`
3. Review the human-readable summary:
   - `uv run scripts/trackio_reporter.py summary --max-jobs 25`
4. Keep the live dashboard open when monitoring parallel runs:
   - `uv run scripts/trackio_reporter.py dashboard --project autolab --mcp-server --no-footer`
5. For continuous reporting:
   - `uv run scripts/trackio_reporter.py sync --project autolab --watch --interval 300`

## What To Watch

- active experiment jobs versus non-experiment jobs
- duplicate active jobs for the same bead or hypothesis
- per-bead `prepare` jobs, which usually indicate wasted bootstrap work
- worker nudges, escalations, and session deaths from `~/gt/.events.jsonl`
- leaderboard entries that actually beat current hub master

## Guardrails

- Treat the reporter as the source of truth for fleet status, not stale shell
  output from one worker.
- If the reporter shows anomalies, fix those before launching more work into
  the same queue.
- Use the reporter to decide whether parallel capacity is real. A slot occupied
  by a duplicate or bootstrap job is not useful parallelism.

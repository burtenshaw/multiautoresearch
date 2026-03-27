# autolab-rig

Concrete repository for running autolab with Gas Town and Codex CLI.

This repo is the source of truth for:

- the live benchmark harness at repo root
- local research notes and seeded hub snapshots under `research/`
- Gas Town rig assets under `gastown/`

It is intentionally separate from the Gas Town source repo. Keep reusable
orchestration code in `autoresearch-gastown`. Keep live autolab work here.

## Layout

- `train.py`
  Working experiment file. This is the only file most experiments should edit.
- `train_orig.py`
  Local copy of the current hub master used as the diff base.
- `prepare.py`
  Read-only benchmark setup and evaluation logic.
- `run-local.sh`
  Canonical timed local run wrapper.
- `scripts/hf_job.py`
  Render, launch, inspect, and stream Hugging Face Jobs for the benchmark rig.
- `scripts/trackio_reporter.py`
  Sync HF Jobs into a local Trackio project and run the local dashboard.
- `sitecustomize.py`
  Machine-local compatibility shim for local runs. Keep local hacks here, not in
  submitted diffs.
- `scripts/refresh_master.py`
  Refresh `train.py`, `train_orig.py`, and live hub snapshots from the autolab
  API.
- `scripts/submit_patch.py`
  Generate a unified diff and submit it to the autolab API.
- `scripts/parse_metric.py`
  Parse the final metric block from a local run log.
- `scripts/install-rig-assets.sh`
  Copy the checked-in Gas Town rig assets into a live `~/gt/<rig>/` layout.
- `gastown/`
  Rig directives, overlays, templates, and operating docs for the live Gas Town
  rig.
- `research/`
  Seed snapshots, local notes, archived diffs, and git-tracked experiment memory.
  This includes `research/paper-ideas.md` for literature-derived hypotheses.

## Quick Start

1. Load credentials:

```bash
. ~/.autolab/credentials
```

2. Authenticate to Hugging Face Jobs and create the shared cache bucket once:

```bash
hf auth whoami
hf buckets create "$AUTOLAB_HF_BUCKET" --private --exist-ok
python3 scripts/hf_job.py launch --mode prepare
```

3. Refresh to current hub master:

```bash
python3 scripts/refresh_master.py --fetch-dag
```

4. Launch one managed benchmark job:

```bash
python3 scripts/hf_job.py preflight
python3 scripts/hf_job.py launch --mode experiment
# note the job id from the JSON output, then:
python3 scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log
python3 scripts/parse_metric.py /tmp/autolab-run.log
```

5. Start local Trackio reporting:

```bash
uv run scripts/trackio_reporter.py sync --project autolab
uv run scripts/trackio_reporter.py dashboard --project autolab --mcp-server --no-footer
```

The reporter summary now calls out duplicate active jobs, bead-scoped `prepare`
jobs, and recent worker nudges or escalations so you can recover paid slots
before launching more work.

6. If the result beats current master, submit it:

```bash
python3 scripts/submit_patch.py --comment "one-sentence hypothesis and result"
```

`run-local.sh` remains available as a local-H100 fallback, but the checked-in
rig defaults to Hugging Face Jobs.

## Gas Town Setup

After creating a live rig from this repo:

```bash
gt rig add autolab <repo-url>
./scripts/install-rig-assets.sh ~/gt/autolab
./scripts/install-rig-assets.sh --check ~/gt/autolab
```

That installs the checked-in planner and polecat directives plus the autolab
formula overlay into the rig container where Gas Town expects them. Use
`--check` to confirm the live rig still matches the checked-in assets, and rerun
the install command if it reports drift. The install also copies
`research/paper-ideas.md` into the live rig root so a dedicated `researcher`
crew worker can maintain literature findings outside any one crew clone.

To add a dedicated paper-scout worker:

```bash
gt crew add researcher --rig autolab
gt crew add reporter --rig autolab
```

The live `crew` directive treats the workspace named `researcher` as a
literature scout that searches Hugging Face papers and feeds the planner
single-change Autolab hypotheses. The workspace named `reporter` maintains the
local Trackio experiment board from HF Jobs status and logs.

## Push Policy

- Push harness changes, notes, helper scripts, and rig assets to this repo.
- Submit winning `train.py` diffs to the autolab hub via the API.
- Do not treat failed experiments as merge-worthy code history. Keep most of that
  memory in `research/` and in beads when using Gas Town.

## Current Seeds

The repo is bootstrapped with the existing local work from `autolab/`:

- current benchmark files at repo root
- seed hub snapshots in `research/reference/`
- experiment notes in `research/notes.md`
- archived failed diff in `research/diffs/batch96.diff`
- Gas Town autolab scaffold in `gastown/`

## See Also

- `docs/gastown-codex-guide.md`
- `gastown/day-1-checklist.md`
- `gastown/templates/experiment-bead.md`

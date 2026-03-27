# Agent Instructions

This repo is a live autolab experiment repo.

## Goal

Lower `val_bpb` on the autolab benchmark with disciplined, comparable
single-change experiments.

## Hard Rules

- Edit `train.py` only unless the task explicitly says otherwise.
- Never modify `prepare.py`.
- Start from current hub master, not stale local history.
- Make exactly one hypothesis change per run.
- Run the timed benchmark before claiming success.
- Submit only if local `val_bpb` beats current master.
- Keep machine-local compatibility shims out of submitted diffs.

## Managed Runner

The default benchmark path in this repo is Hugging Face Jobs, not a local CUDA
host.

One-time bootstrap:
- `hf auth whoami`
- `hf buckets create "$AUTOLAB_HF_BUCKET" --private --exist-ok`
- `python3 scripts/hf_job.py launch --mode prepare`

Per experiment:
- `python3 scripts/hf_job.py launch --mode experiment`
- note the job id from the output
- `python3 scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log`
- `python3 scripts/parse_metric.py /tmp/autolab-run.log`

## Standard Workflow

1. Refresh from the hub:
   - `python3 scripts/refresh_master.py --fetch-dag`
2. Edit `train.py`.
3. Launch one managed benchmark job:
   - `python3 scripts/hf_job.py launch --mode experiment`
   - `python3 scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log`
4. Parse the result:
   - `python3 scripts/parse_metric.py /tmp/autolab-run.log`
5. Record the hypothesis and outcome in `research/notes.md`.
6. Submit if improved:
   - `python3 scripts/submit_patch.py --comment "..."`

## Repo Layout

- Root benchmark files are the experiment surface.
- `research/` is the durable experiment notebook.
- `gastown/` contains the rig assets that should be installed into a live
  `~/gt/<rig>/` container with `scripts/install-rig-assets.sh`.

## Literature Scouting

When the task is planner or literature research rather than a timed benchmark
run:

- You may edit `research/*.md`, `gastown/`, and operator docs.
- Use the local `hf-cli` skill plus Hugging Face paper search and read tooling
  to find relevant work.
- Translate papers into single-change `train.py` hypotheses that can be tested
  cleanly.
- Record paper-derived ideas in `research/paper-ideas.md`.
- Do not claim a win or submit a patch without a benchmark run.

## Local Compatibility

`run-local.sh` sets `AUTOLAB_FORCE_FA3_REDIRECT=1`, and `sitecustomize.py`
redirects the Hopper FA3 kernel lookup for hosts that cannot import the default
wheel locally. Do not bake that redirect into `train.py`. Keep `run-local.sh`
as a local fallback only; do not use it as the default rig path.

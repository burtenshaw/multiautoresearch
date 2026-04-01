# Script Reference

These scripts are the public operator entrypoints for this repo.

## Summary

| Script | Purpose | External Systems |
| --- | --- | --- |
| `scripts/refresh_master.py` | Restore `train.py` from the current local promoted master and rebuild live metadata | Local files only |
| `scripts/hf_job.py` | Preflight, render, launch, inspect, and tail managed HF Jobs | Hugging Face Jobs, local files |
| `scripts/opencode_worker.py` | Create, run, and clean isolated OpenCode experiment worktrees | Git worktrees, OpenCode, local files |
| `scripts/print_opencode_kickoff.py` | Print a parent-session kickoff prompt | Local files only |
| `scripts/parse_metric.py` | Parse the final metric block from a run log | Local files only |
| `scripts/submit_patch.py` | Append a run to `research/results.tsv` and locally promote if it wins | Local files, optional Hugging Face Jobs logs |
| `scripts/sync_upstream.py` | Diff or apply upstream-tracked core files from `karpathy/autoresearch` | GitHub raw files |
| `scripts/trackio_reporter.py` | Sync jobs to Trackio and render a local dashboard | Hugging Face Jobs, Trackio, local files |

## `scripts/refresh_master.py`

- Inputs:
  - `--fetch-dag`
  - `--force`
- Environment:
  - none
- Outputs:
  - rewrites `train.py`, `train_orig.py`, and files under `research/live/`
- Use when:
  - starting any fresh benchmark run
  - restoring the checkout to the current promoted local master

## `scripts/hf_job.py`

- Inputs:
  - `preflight`, `render`, `launch`, `inspect`, `logs`
- Environment:
  - `AUTOLAB_HF_BUCKET` required for `prepare` and `experiment`
  - `AUTOLAB_HF_NAMESPACE` optional
  - `AUTOLAB_CAMPAIGN` optional
  - `AUTOLAB_EXPERIMENT_ID` optional
  - `AUTOLAB_WORKER_ID` optional
  - `AUTOLAB_HYPOTHESIS` optional
  - `AUTOLAB_HF_PREPARE_FLAVOR`, `AUTOLAB_HF_PREPARE_TIMEOUT`
  - `AUTOLAB_HF_EXPERIMENT_FLAVOR`, `AUTOLAB_HF_EXPERIMENT_TIMEOUT`
  - `AUTOLAB_HF_CLI` optional
  - `AUTOLAB_HF_SECRETS` optional
- Outputs:
  - rendered job bundles under `.runtime/`
  - job metadata under `.runtime/hf-jobs/`
  - cached logs under `.runtime/hf-logs/`
  - streamed logs when requested
- Use when:
  - validating a workspace before launch
  - starting and monitoring managed benchmark runs

## `scripts/opencode_worker.py`

- Inputs:
  - `create`, `run`, `cleanup`
- Environment:
  - `AUTOLAB_OPENCODE_BIN` optional override for the OpenCode executable
- Outputs:
  - isolated worktrees under `.runtime/worktrees/`
  - worker state under `.runtime/opencode-workers/`
  - experiment notes under `research/experiments/`
  - reserved run logs under `research/live/`
- Use when:
  - launching an `experiment-worker` in a filesystem-isolated checkout
  - keeping parallel paid runs from colliding in the main checkout

## `scripts/print_opencode_kickoff.py`

- Inputs:
  - optional `--campaign`, `--gpu-slots`, `--max-ideas`
- Environment:
  - none
- Outputs:
  - a standard parent-session prompt to stdout
- Use when:
  - starting a fresh OpenCode planning session in the repo root

## `scripts/parse_metric.py`

- Inputs:
  - a path to a job or local run log
- Environment:
  - none
- Outputs:
  - JSON metric block to stdout
- Use when:
  - extracting `val_bpb`, timing, and utilization metrics after a completed run

## `scripts/submit_patch.py`

- Inputs:
  - `--comment`
  - optional `--priority`, `--parent-hash`, `--job-id`, `--log`, `--dry-run`
- Environment:
  - `AUTOLAB_HF_CLI` optional when the command needs to fetch uncached HF Job logs
  - `AUTOLAB_HF_NAMESPACE` optional when the command needs to fetch uncached HF Job logs
- Outputs:
  - appends a row to `research/results.tsv`
  - updates `train_orig.py` and `research/live/` only when the result beats current master
- Use when:
  - recording a completed managed benchmark run
  - promoting a new local master after a real improvement

## `scripts/sync_upstream.py`

- Inputs:
  - optional `--check`, `--apply`, `--branch`, `--timeout`
- Environment:
  - none
- Outputs:
  - unified diffs against upstream-tracked files
  - optional in-place updates for `prepare.py`, `train.py`, `program.md`, `pyproject.toml`, and `uv.lock`
- Use when:
  - comparing the repo's upstream-tracked files against `karpathy/autoresearch`
  - explicitly applying upstream file updates without touching the local results ledger

## `scripts/trackio_reporter.py`

- Inputs:
  - `sync`, `dashboard`, `summary`
- Environment:
  - `AUTOLAB_TRACKIO_PROJECT` optional, defaults to `autolab`
  - `AUTOLAB_HF_NAMESPACE` recommended
  - `AUTOLAB_HF_CLI` optional
  - `AUTOLAB_TRACKIO_BIN` optional
- Outputs:
  - local reporter state and markdown summaries under `.runtime/`
  - merged job views from `.runtime/hf-jobs/*.json` and `.runtime/worktrees/*/.runtime/hf-jobs/*.json`
  - Trackio runs and dashboard output
- Use when:
  - checking active jobs
  - finding duplicate experiment or hypothesis launches
  - monitoring experiment results locally

# Getting Started

This repo is a self-contained Autolab operator checkout. It uses a local
promoted master plus Hugging Face Jobs and Trackio.

## Prerequisites

- Python 3.10 or newer
- `uv`
- `hf` CLI
- `opencode`
- a Hugging Face account with Jobs access

## 1. Clone And Install

```bash
git clone <repo-url>
cd <repo-dir>
uv sync
```

## 2. Create Local Operator Env

```bash
mkdir -p ~/.autolab
cp .autolab.credentials.example ~/.autolab/credentials
$EDITOR ~/.autolab/credentials
. ~/.autolab/credentials
```

The env file stays in your home directory, not in the repo.

## 3. Validate Your Setup

```bash
bash scripts/bootstrap_public.sh
```

This checks:

- `python3`, `uv`, and `hf`
- Python version compatibility
- local Hugging Face auth with `hf auth whoami`
- `AUTOLAB_HF_BUCKET`
- shared HF cache bucket creation

It prints the next commands without starting paid jobs.

## 4. Authenticate Hugging Face And Bootstrap Shared Cache

```bash
hf auth login
hf auth whoami
hf buckets create "$AUTOLAB_HF_BUCKET" --private --exist-ok
uv run scripts/hf_job.py launch --mode prepare
```

This prime step keeps tokenizer and data bootstrap out of your paid experiment
loop.

## 5. Refresh To Current Local Master

```bash
uv run scripts/refresh_master.py --fetch-dag
```

This rewrites:

- `train.py`
- `train_orig.py`
- `research/live/master.json`
- `research/live/master_detail.json`
- `research/live/dag.json`

Do not use repo git history as benchmark truth. Use the refreshed files above
plus `research/results.tsv`.

## 6. Authenticate OpenCode And Choose A Model

```bash
opencode auth login
opencode
# inside OpenCode:
/models
```

Choose Hugging Face and an open model through Hugging Face Inference Providers.
Do not pin a single exact model id in repo config.

## 7. Start The Parent Session

```bash
uv run scripts/print_opencode_kickoff.py --gpu-slots 1
opencode
```

Use the `autolab` primary agent from the repo root. For the full parent and
worker flow, continue with [opencode-workflow.md](opencode-workflow.md).

## 8. Run One Managed Experiment

Edit `train.py`, or launch an isolated worker with
`uv run scripts/opencode_worker.py create ...` and
`uv run scripts/opencode_worker.py run ...`, then run:

```bash
uv run scripts/hf_job.py preflight
uv run scripts/hf_job.py launch --mode experiment
uv run scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log
uv run scripts/parse_metric.py /tmp/autolab-run.log
```

Rules:

- one hypothesis change only
- `train.py` only unless explicitly authorized otherwise
- do not modify `prepare.py`

## 9. Record The Run Locally

Every completed run should be appended to the local ledger:

```bash
uv run scripts/submit_patch.py --comment "one-sentence hypothesis and observed val_bpb"
```

This always records the run in `research/results.tsv`. It promotes the local
master only when the observed `val_bpb` beats current master.

## 10. Optional: Local Trackio Dashboard

```bash
uv run scripts/trackio_reporter.py sync --project "${AUTOLAB_TRACKIO_PROJECT:-autolab}"
uv run scripts/trackio_reporter.py dashboard --project "${AUTOLAB_TRACKIO_PROJECT:-autolab}" --mcp-server --no-footer
```

Use the reporter summary before launching more work:

```bash
uv run scripts/trackio_reporter.py summary --max-jobs 25
```

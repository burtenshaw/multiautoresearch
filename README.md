# autolab-rig

Public operator repository for running Autolab experiments with Hugging Face
Jobs and, optionally, Gas Town.

The default path is simple:

1. clone the repo
2. add your local Autolab credentials
3. log into Hugging Face
4. run the bootstrap check
5. refresh benchmark master
6. launch one managed experiment

This repo does **not** bundle the Autolab backend itself. You need access to a
hosted Autolab service plus Hugging Face Jobs.

## What You Need

- Python 3.10 or newer
- `uv`
- `hf` CLI
- a Hugging Face account with Jobs access
- a hosted Autolab account, endpoint, and API key
- optional: Gas Town if you want planner/polecat orchestration

## Start Here

If you only want to try the project, use the direct operator path below. You do
not need Gas Town for a first run.

### 1. Clone And Install

```bash
git clone https://github.com/burtenshaw/autolab-gastown.git
cd autolab-gastown
uv sync
```

### 2. Create Local Credentials

```bash
mkdir -p ~/.autolab
cp .autolab.credentials.example ~/.autolab/credentials
$EDITOR ~/.autolab/credentials
```

Your credentials file stays in your home directory, not in the repo.

### 3. Log In To Hugging Face Once

```bash
hf auth login
```

### 4. Validate Your Setup

```bash
. ~/.autolab/credentials
bash scripts/bootstrap_public.sh
```

This verifies:

- `python3`, `uv`, and `hf`
- your local Hugging Face login
- required Autolab and HF environment variables
- shared HF bucket access

If this step fails, start with [docs/troubleshooting.md](docs/troubleshooting.md).

### 5. Warm The Shared Cache Once

```bash
python3 scripts/hf_job.py launch --mode prepare
```

### 6. Refresh Current Benchmark Master

```bash
python3 scripts/refresh_master.py --fetch-dag
```

This rewrites `train.py`, `train_orig.py`, and `research/live/*`. Treat those
files as the benchmark source of truth. Do **not** use repo git history such as
`main` or `origin/main` as benchmark truth.

### 7. Make One Change In `train.py`

Most experiments should edit `train.py` only.

### 8. Launch One Managed Experiment

```bash
python3 scripts/hf_job.py preflight
python3 scripts/hf_job.py launch --mode experiment
python3 scripts/hf_job.py logs <JOB_ID> --follow --output /tmp/autolab-run.log
python3 scripts/parse_metric.py /tmp/autolab-run.log
```

### 9. Submit Only If You Beat Master

```bash
python3 scripts/submit_patch.py --comment "one-sentence hypothesis and observed val_bpb"
```

## First Run Rules

- Refresh from hosted master before every fresh experiment.
- Use `train.py`, `train_orig.py`, and `research/live/master.json` as benchmark
  truth.
- Make exactly one hypothesis change per run.
- Do not modify `prepare.py`.
- Submit only if observed `val_bpb` beats current master.

## Optional: Local Trackio Dashboard

```bash
uv run scripts/trackio_reporter.py sync --project "${AUTOLAB_TRACKIO_PROJECT:-autolab}"
uv run scripts/trackio_reporter.py dashboard --project "${AUTOLAB_TRACKIO_PROJECT:-autolab}" --mcp-server --no-footer
```

## Stable Public Entrypoints

These scripts are the operator-facing interface of the repo:

- `scripts/refresh_master.py`
- `scripts/hf_job.py`
- `scripts/parse_metric.py`
- `scripts/submit_patch.py`
- `scripts/trackio_reporter.py`

See [docs/script-reference.md](docs/script-reference.md) for inputs,
environment variables, outputs, and external dependencies.

## Supported Modes

### Direct Operator Mode

Use the scripts directly from this checkout. This is the recommended path for a
new operator and does not require Gas Town.

### Gas Town Mode

Once the direct path makes sense, you can add planner, polecat, researcher, and
reporter workers:

```bash
gt rig add autolab <repo-url>
./scripts/install-rig-assets.sh ~/gt/autolab
./scripts/install-rig-assets.sh --check ~/gt/autolab
```

Then continue with [docs/gastown.md](docs/gastown.md).

## Contribution Model

- Repo changes such as docs, helper scripts, and rig assets belong in git
  history here.
- Winning `train.py` diffs belong in the hosted Autolab submission system via
  `scripts/submit_patch.py`.
- Failed experiment history belongs in `research/notes.md`, Trackio, or Gas
  Town beads, not as a long tail of repo commits.

## Docs

- [docs/getting-started.md](docs/getting-started.md)
- [docs/hosted-backend.md](docs/hosted-backend.md)
- [docs/script-reference.md](docs/script-reference.md)
- [docs/gastown.md](docs/gastown.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/gastown-codex-guide.md](docs/gastown-codex-guide.md)

## License

This repository is released under the [MIT License](LICENSE).

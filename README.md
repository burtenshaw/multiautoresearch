# Multi-Agent Autoresearch

This repo is a self-contained Open Source AI Lab that researches papers, manages experiments, runs GPUs, and repeats. It is based on [autoresearch](https://github.com/karpathy/autoresearch) by Andrej Karpathy.

<img width="2468" height="985" alt="gastown_wave2_running_jobs" src="https://github.com/user-attachments/assets/e1ae62ed-7a7a-4ba3-9e68-6fa97a4d86c8" />

OpenCode is the primary way to use this repo. The checked-in agents and [`AGENTS.md`](/Users/ben/code/open-autolab/AGENTS.md) tell the agent which scripts to run and how to use them safely. Hoever, there are also implementations for Codex and Claude Code.

## What This Repo Contains

- `train.py`
  The working experiment surface.
- `prepare.py`
  Read-only benchmark setup and evaluation logic.
- `research/results.tsv`
  Append-only local run ledger.
- `research/live/`
  The current promoted local master snapshot and DAG.
- `research/`
  Notes, campaign state, experiment records, and templates.
- `.opencode/agent/`
  The checked-in OpenCode agents: `autolab`, `planner`, `experiment-worker`,
  `reviewer`, `memory-keeper`, `researcher`, and `reporter`.
- `.agents/skills/`
  Shared repo-local skills.

## Local Setup

Install the repo and create your local operator env:

```bash
uv sync
hf auth login
hf auth whoami
opencode auth login
```

If you have not warmed the shared Hugging Face cache yet, you can ask OpenCode
to do that as part of the first session. The exact script path is already in
[`AGENTS.md`](/Users/ben/code/open-autolab/AGENTS.md).

## Start OpenCode

From the repo root:

```bash
opencode
```

Use the `autolab` primary agent. The normal pattern is:

1. Open OpenCode in the repo root.
2. Give the `autolab` agent a short goal.
3. Let the repo agents and `AGENTS.md` drive the scripts.

You do not need to memorize the benchmark commands from the README.

## Simple Prompts

Use prompts like these with the `autolab` agent:

- `Refresh the local promoted master, review the notebook, and propose up to 3 fresh single-change experiments.`
- `Check whether the shared HF cache is ready. If not, run the one-time prepare path, then refresh local master.`
- `Create one isolated worker for a warmdown-ratio experiment, launch it, and tell me the experiment id, job id, and log path.`
- `Review the current reporter state and tell me whether any active experiments are duplicated or stale.`
- `Take the latest completed run, record it locally, tell me whether it promoted, and draft the note for memory-keeper.`
- `Compare this repo's upstream-tracked files against karpathy/autoresearch and summarize the diffs without applying them.`

If you want a longer parent-session kickoff prompt, run:

```bash
uv run scripts/print_opencode_kickoff.py --gpu-slots 1
```

## Autonomous Run Example

One concrete way to send off an autonomous local autoresearch session is:

1. Make sure your local env is loaded and the shared Hugging Face bucket exists:

```bash
. ~/.autolab/credentials
hf buckets create "$AUTOLAB_HF_BUCKET" --private --exist-ok
opencode
```

2. In OpenCode, use the `autolab` primary agent with a prompt like:

```text
Run one autonomous local autoresearch pass in this repo using the repo-defined roles.

Use planner to propose up to 2 fresh single-change experiments against the current local promoted master.
Use reviewer to reject duplicates or stale ideas before any paid run starts.
If the shared HF cache is not ready, run the one-time prepare path using the configured HF bucket.
Then refresh the local promoted master.

For the best approved experiment, create one isolated experiment-worker worktree and launch it through Hugging Face Jobs.
Use HF Jobs for the benchmark run, the shared HF bucket for cache/data mounting, and the reserved experiment log path.
When the run finishes, parse the metric, record it locally, tell me whether it promoted, and hand the durable note text to memory-keeper.
Use reporter at the end to summarize active jobs, anomalies, and the current leader.

Use as many concurrent experiment-workers as possible.
Do not stop until all you have completed a full pass of successful experiments.
```

That prompt is enough for the checked-in agents plus
[`AGENTS.md`](/Users/ben/code/open-autolab/AGENTS.md) to route the work through
the repo scripts, HF Jobs, HF buckets, and the local results ledger.

## Operating Model

- Refresh from the current local promoted master before a fresh experiment.
- Edit `train.py` only unless the task explicitly says otherwise.
- Never modify `prepare.py`.
- Make exactly one hypothesis change per run.
- Record every completed run in `research/results.tsv`.
- Local promotion only happens when observed `val_bpb` beats current master.

## Where To Look Next

- [`AGENTS.md`](/Users/ben/code/open-autolab/AGENTS.md)
  Repo rules and the agent operating contract.
- [docs/opencode-workflow.md](/Users/ben/code/open-autolab/docs/opencode-workflow.md)
  Full parent-session and worker workflow.
- [docs/claude-subagents-guide.md](/Users/ben/code/open-autolab/docs/claude-subagents-guide.md)
  Optional secondary Claude Code-native integration.
- [docs/codex-subagents-guide.md](/Users/ben/code/open-autolab/docs/codex-subagents-guide.md)
  Optional secondary Codex-native integration.
- [docs/script-reference.md](/Users/ben/code/open-autolab/docs/script-reference.md)
  Direct script interfaces, if you need them.
- [docs/getting-started.md](/Users/ben/code/open-autolab/docs/getting-started.md)
  More detailed local setup notes.
- [docs/troubleshooting.md](/Users/ben/code/open-autolab/docs/troubleshooting.md)
  Common local operator issues.

## Contribution Model

- Tooling, docs, templates, and control-plane changes belong in git history
  here.
- Benchmark runs are recorded locally in `research/results.tsv`.
- Current-master promotions happen locally from recorded winning runs.
- Failed experiment history belongs in `research/notes.md`,
  `research/do-not-repeat.md`, `research/experiments/`, and Trackio, not as a
  long tail of benchmark commits.

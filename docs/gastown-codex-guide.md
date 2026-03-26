# Winning Autolab With Gas Town and Codex CLI

This guide shows how to use Gas Town as the coordination layer and Codex CLI as
the worker runtime for autolab.

The goal is not to maximize agent count. The goal is to maximize useful,
non-duplicated experiments per H100-hour until you beat current master on
`val_bpb`.

## What Autolab Rewards

- One fixed 5-minute training budget on a single H100 GPU.
- One score: `val_bpb`. Lower is better.
- `prepare.py` is read-only.
- `train.py` is the file you optimize.
- Submissions are unified diffs against current master.

Autolab is mostly a coordination problem:

- Read the full experiment history before proposing new work.
- Keep a durable do-not-repeat memory.
- Dispatch only one fresh hypothesis per GPU slot.
- Stop stale-master work quickly.
- Submit only real improvements.

Gas Town helps with exactly those problems:

- `crew` or `mayor` plans the research program.
- `polecats` run one benchmark experiment each.
- `beads` store hypotheses, results, and dead ends.
- `convoys` group related experiment campaigns.
- `witness` keeps worker hygiene tight.

## Use This Repo As The Scaffold

The checked-in `autolab/` directory is the scaffold for a real rig:

- `autolab/directives/crew.md`
  Planner policy.
- `autolab/directives/polecat.md`
  Worker policy.
- `autolab/formula-overlays/mol-polecat-work.toml`
  Formula override that turns generic polecat work into an experiment loop.
- `autolab/taxonomy.md`
  Bead labels and required metadata.
- `autolab/convoys.md`
  Convoy naming and grouping rules.
- `autolab/templates/experiment-bead.md`
  Template for one experiment bead.
- `autolab/templates/convoy-template.md`
  Template for one research campaign.
- `autolab/day-1-checklist.md`
  Short launch checklist.

Install those policies into the live rig before you scale worker count.

Examples below assume the rig is named `autolab`. Replace that with your real
rig name if needed.

## The Winning Role Split

Use a strict split between planning and execution.

### Planner: `crew` or `mayor`

The planner owns strategy:

- fetch current master and recent hub activity
- read the full DAG and recent messages
- maintain a short queue of non-overlapping ideas
- create or update experiment beads
- group work into narrow convoys
- keep a live do-not-repeat ledger

The planner should not spend GPU time unless there is no idle worker and the
next experiment is urgent.

### Polecats

Polecats execute one experiment cleanly:

- start from current master only
- modify `train.py` only unless explicitly authorized otherwise
- make exactly one hypothesis change
- run the timed benchmark
- record `val_bpb` and a short interpretation
- submit only if they beat current master

### Witness

Witness is not a researcher. It is a hygiene monitor:

- detect stale or duplicated workers
- nudge blocked polecats
- surface collision patterns to the planner

## Configure Gas Town To Use Codex CLI

Gas Town already supports `codex` as a runtime. Set an alias you like and make
it the default for this rig or town:

```bash
gt config agent list
gt config agent set codex-low "codex --thinking low"
gt config default-agent codex-low
```

Override per assignment when needed:

```bash
gt sling <bead-id> autolab --agent codex-low
```

Start in minimal mode first. It is easier to debug than a full autonomous
daemon swarm:

```bash
gt convoy create "optimizer: initial follow-ups" <bead-id>
gt sling <bead-id> autolab --agent codex-low
cd ~/gt/autolab/polecats/<worker-name>/rig
codex
```

If a session comes up without full role context, run:

```bash
gt prime
```

Only move to daemon-managed full stack mode after duplicate prevention and
result persistence are working.

## Keep GPU Capacity Honest

Treat `scheduler.max_polecats` as the GPU governor.

Rules:

- one validated comparable runner = one active experiment polecat
- start with one planner and one polecat
- add more polecats only after the planner is consistently preventing duplicates
- do not launch idle workers just because the machine can host more terminals

More workers do not help if they burn the same hypothesis twice.

## Autolab Setup

### 1. Verify hardware

```bash
nvidia-smi
```

If `nvidia-smi` is missing, if the visible GPU is not an NVIDIA H100, or if the
checked-in local benchmark path cannot run on that host, stop. Local
comparisons are not trustworthy otherwise.

This includes wrapper prerequisites. A shell that lacks basics such as
`timeout`, CUDA wheels, or the checked-in benchmark path is not a comparable
runner, even if it can host idle polecats.

### 2. Register or load credentials

If credentials already exist:

```bash
. ~/.autolab/credentials
echo "Loaded existing autolab credentials"
```

If not, register once:

```bash
export NICKNAME="your-name"
RESPONSE=$(curl -sS -X POST "http://autoresearchhub.com/api/register" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"$NICKNAME\"}")

API_KEY=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["api_key"])' \
  <<<"$RESPONSE")

mkdir -p ~/.autolab
cat > ~/.autolab/credentials <<EOF
AUTOLAB=http://autoresearchhub.com
AUTOLAB_KEY=$API_KEY
EOF
chmod 600 ~/.autolab/credentials
. ~/.autolab/credentials
```

If registration fails because the name is taken, pick a different nickname and
retry.

### 3. Assign GPUs intentionally

Run `nvidia-smi`, pick a GPU index per worker, and never let two experiment
polecats fight over the same H100.

### 4. Prepare a benchmark workspace

You can use the checked-in scaffold in `autolab/contributor/` or create a clean
workspace elsewhere. Either way:

- treat `prepare.py` as read-only
- keep the live master source in `train_orig.py`
- edit only `train.py`

The checked-in contributor directory already includes:

- `run-local.sh` for timed runs
- `sitecustomize.py` for machine-local compatibility shims
- `notes.md` for local baseline notes

Machine-specific hacks belong in local wrappers, not in submitted diffs.

## Read The Swarm Before You Touch `train.py`

Before the first experiment of the day, fetch the current state of the hub:

```bash
. ~/.autolab/credentials
curl -sS "$AUTOLAB/api/git/dag" > /tmp/autolab-dag.json
curl -sS "$AUTOLAB/api/git/master" > /tmp/autolab-master.json
```

The planner should then:

1. Sort the DAG chronologically.
2. Identify the improvement chain: every run that was a new best at the time.
3. Read every winning and near-miss message.
4. Note repeated regressions and convert them into do-not-repeat memory.
5. Fetch diffs for the most informative breakthroughs.

Get the current master source:

```bash
MASTER_HASH=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["hash"])' \
  < /tmp/autolab-master.json)
curl -sS "$AUTOLAB/api/git/commits/$MASTER_HASH" > /tmp/autolab-master-detail.json
```

If you want to materialize `train.py` from the API response:

```bash
python3 <<'PY'
import json
from pathlib import Path

detail = json.load(open("/tmp/autolab-master-detail.json"))
Path("train_orig.py").write_text(detail["source"])
Path("train.py").write_text(detail["source"])
PY
```

Do this before dispatching work. Blind brainstorming loses to teams that read
the DAG carefully.

## Planner Workflow

Use `crew` for the planner because it is persistent and easier to steer.

Suggested loop:

1. Fetch current master, recent commits, and any new diffs.
2. Update the do-not-repeat ledger from regressions and duplicates.
3. Confirm that at least one validated comparable runner is currently available.
4. Pick a narrow convoy theme.
5. Create one bead per hypothesis only if a comparable runner exists, and name the target comparable runner in the bead.
6. Dispatch only up to validated comparable-runner capacity.

Use convoys for research campaigns, not random batches. Follow the naming rule
from `autolab/convoys.md`:

`<theme>: <specific branch of inquiry>`

Good examples:

- `optimizer: lower beta2 without architecture change`
- `throughput: smaller model for more tokens in 5 minutes`
- `recent-master: follow-ups after new winning patch`

Each experiment bead should include, at minimum:

- one-sentence hypothesis
- parent master hash
- master `val_bpb` at dispatch time
- intended comparable runner or capability proof
- exact single variable being changed
- expected upside
- reason it is not a duplicate

Use `autolab/templates/experiment-bead.md` and
`autolab/templates/convoy-template.md` instead of inventing a free-form format.

If no validated comparable runner is available, do not mint or sling the bead.
Leave it unslung or blocked with an explicit note such as `waiting for
comparable runner` until a trusted H100 host or proven comparable managed
runner is available.

For bead workflow:

```bash
bd ready
bd create --title="optimizer: lower final lr floor" --type=task --priority=1
bd show <id>
gt convoy create "optimizer: final-lr follow-ups" <id>
gt sling <id> autolab --agent codex-low
```

If you use `bv`, never run bare `bv`. Use only the robot modes:

```bash
bv --robot-triage
bv --robot-plan
bv --robot-alerts
```

## Polecat Workflow

Polecats are execution workers, not free-roaming researchers.

Before editing:

1. Run `gt prime` if role context is missing.
2. Read the assigned bead.
3. Verify that your current execution path is actually comparable:
   - local path: `nvidia-smi` exists, shows an NVIDIA H100, and `./run-local.sh` prerequisites are present
   - managed path: the bead explicitly targets a runner that has already produced trusted comparable results
4. If the capability gate fails, stop before editing and record `waiting for comparable runner` instead of trying the run locally.
5. Re-fetch current master.
6. Confirm the hypothesis is still fresh.
7. Confirm the allowed edit scope is still `train.py` only.

Execution contract:

1. Start from current master, not from yesterday's local edits.
2. Change exactly one variable.
3. Run one timed local experiment.
4. Record the result even if it regressed.
5. Submit only if local `val_bpb` beats current master.

Generic local run:

```bash
CUDA_VISIBLE_DEVICES=$GPU timeout 600 uv run train.py 2>&1 | tee /tmp/autolab-run.log
```

If you are using the checked-in contributor workspace, prefer:

```bash
cd autolab/contributor
CUDA_VISIBLE_DEVICES=$GPU ./run-local.sh /tmp/autolab-run.log
```

Extract the metric from the log:

```bash
python3 <<'PY'
import re
from pathlib import Path

text = Path("/tmp/autolab-run.log").read_text()
match = re.search(r"val_bpb:\s+([0-9.]+)", text)
print(match.group(1) if match else "MISSING")
PY
```

If the `val_bpb:` line is missing, the run is a failed experiment. Record why and
do not submit.

If master changed materially while the run was in flight, persist that fact and
ask for replanning. Do not improvise from stale context.

## Submission Workflow

If local `val_bpb` is better than the hub master, generate a unified diff:

```bash
diff -u train_orig.py train.py > /tmp/autolab-diff.txt || true
```

Submit with Python building the JSON payload so special characters in the diff do
not break the request:

```bash
export MASTER_HASH="<current-master-hash>"
export COMMENT="one-sentence hypothesis plus observed local val_bpb"

python3 <<'PY'
import json
import os
import pathlib
import subprocess

payload = json.dumps({
    "parent_hash": os.environ["MASTER_HASH"],
    "diff": pathlib.Path("/tmp/autolab-diff.txt").read_text(),
    "comment": os.environ["COMMENT"],
    "priority": 0,
})

subprocess.run(
    [
        "curl",
        "-sS",
        "-X", "POST",
        f"{os.environ['AUTOLAB']}/api/patches",
        "-H", f"Authorization: Bearer {os.environ['AUTOLAB_KEY']}",
        "-H", "Content-Type: application/json",
        "-d", payload,
    ],
    check=True,
)
PY
```

Do not try to inline the diff directly into a shell JSON string.

After the submit or no-submit decision, persist:

- parent master hash
- local `val_bpb`
- hypothesis tested
- whether the patch was submitted
- one short interpretation
- failure mode if the run regressed or was invalid

That persistence is what keeps the next worker from wasting the same slot.

For a one-run experiment bead, closing and syncing immediately is usually the
right move:

```bash
bd close <id>
bd sync
```

## Communication Rules

Use Gas Town communication primitives, not terminal text:

- `gt sling` assigns the bead
- `gt mail send` carries detailed context
- `gt nudge` wakes an active agent immediately

Typical pattern:

1. Planner creates the bead.
2. Planner adds the bead to the right convoy.
3. Planner slings the bead to a polecat.
4. Planner sends mail only if extra experiment context is needed.
5. Witness nudges if the worker goes stale.

## What Actually Wins

The teams that win autolab usually do these things well:

- They read the full research history before generating more ideas.
- They follow up recent wins and strong near-misses instead of chasing novelty.
- They keep one variable per experiment so results are legible.
- They record regressions aggressively.
- They baseline locally before trusting a tiny improvement.
- They keep machine-local compatibility fixes outside the submitted patch.
- They stop stale-master work instead of doubling down on it.
- They scale worker count only after duplicate prevention is solid.

Winning is not "run more agents." Winning is "burn fewer H100 minutes on bad or
repeated ideas."

## Anti-Patterns

Do not:

- let every Codex session choose its own research agenda
- run more polecats than usable GPUs
- bundle optimizer, architecture, and throughput ideas into one patch
- skip DAG reading because the idea sounds obvious
- treat an unrecorded regression as harmless
- edit `prepare.py`
- keep working after master changed materially without replanning

## Useful API Calls

Get current master:

```bash
curl -sS "$AUTOLAB/api/git/master"
```

Get one commit detail, including `train.py` source and diff:

```bash
curl -sS "$AUTOLAB/api/git/commits/<hash>"
```

Get the full experiment DAG:

```bash
curl -sS "$AUTOLAB/api/git/dag"
```

Get recent commits:

```bash
curl -sS "$AUTOLAB/api/git/commits?limit=20"
curl -sS "$AUTOLAB/api/git/commits?since=2025-01-15T10:30:00Z&limit=50"
```

List your recent patches:

```bash
curl -sS "$AUTOLAB/api/patches?limit=10" \
  -H "Authorization: Bearer $AUTOLAB_KEY"
```

Get the leaderboard:

```bash
curl -sS "$AUTOLAB/api/leaderboard"
```

## Short Version

If you want the shortest winning recipe:

1. One planner, one polecat per H100, no more.
2. Read the DAG and current master before every experiment batch.
3. Put each hypothesis in a bead and each theme in a convoy.
4. Constrain polecats to one `train.py` change and one timed run.
5. Record every result.
6. Submit only true improvements.
7. Scale only when the swarm has memory and duplicate prevention.

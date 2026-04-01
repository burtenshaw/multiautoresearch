#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / ".runtime"
WORKTREE_ROOT = RUNTIME_DIR / "worktrees"
STATE_DIR = RUNTIME_DIR / "opencode-workers"
EXPERIMENT_DIR = ROOT / "research" / "experiments"
LIVE_DIR = ROOT / "research" / "live"
MASTER_PATH = LIVE_DIR / "master.json"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, *, default: str = "unknown") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or default


def ensure_id(name: str, value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{name} must match {ID_PATTERN.pattern!r}: {value!r}")
    return value


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd or ROOT, env=env, text=True, capture_output=True, check=False)


def require_tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise SystemExit(f"could not find `{name}` in PATH")


def load_master_snapshot() -> dict[str, object]:
    if not MASTER_PATH.exists():
        return {}
    try:
        payload = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def worker_state_path(experiment_id: str) -> Path:
    return STATE_DIR / f"{experiment_id}.json"


def worktree_path(experiment_id: str) -> Path:
    return WORKTREE_ROOT / experiment_id


def experiment_note_path(experiment_id: str) -> Path:
    return EXPERIMENT_DIR / f"{experiment_id}.md"


def experiment_log_path(experiment_id: str) -> Path:
    return LIVE_DIR / f"{experiment_id}.log"


def write_state(state: dict[str, object]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = worker_state_path(str(state["experiment_id"]))
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_state(experiment_id: str) -> dict[str, object]:
    path = worker_state_path(experiment_id)
    if not path.exists():
        raise SystemExit(f"missing worker state: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"failed to parse worker state {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"unexpected worker state payload in {path}")
    return payload


def ensure_worktree(target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    result = run(["git", "worktree", "add", "--detach", str(target)])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "git worktree add failed")


def build_note(state: dict[str, object]) -> str:
    master_val = state.get("master_val_bpb")
    if isinstance(master_val, (int, float)):
        master_val_text = f"{master_val:.6f}"
    else:
        master_val_text = "<value>"
    return f"""# Experiment: {state["title"]}

## Campaign

- Campaign: `{state["campaign"]}`

## Hypothesis

{state["hypothesis"]}

## Parent Context

- Parent master hash: `{state.get("master_hash") or "<hash>"}`
- Master val_bpb at dispatch: `{master_val_text}`
- Worker id: `{state["worker_id"]}`
- Worktree: `{state["worktree_path"]}`

## Single Variable

<What exact variable, knob, or logic change is being tested?>

## Expected Upside

<Why this might improve val_bpb or effective throughput inside the 5-minute budget>

## Duplicate Check

<Why this is not a duplicate of an open or recent experiment>

## Runtime

- Log path: `{state["log_path"]}`
- Launcher: `uv run scripts/opencode_worker.py run {state["experiment_id"]}`

## Allowed Edit Scope

- `train.py` only

## Run Plan

- Refresh master with `uv run scripts/refresh_master.py --fetch-dag`
- Run `uv run scripts/hf_job.py preflight`
- Run `uv run scripts/hf_job.py launch --mode experiment`
- Stream logs to the reserved path
- Parse `uv run scripts/parse_metric.py {state["log_path"]}`

## Result

- Local val_bpb: `<value>`
- Submitted: `yes|no`
- Interpretation: `<one or two sentences>`
- Failure mode, if any: `<brief note>`

## Memory-Keeper Handoff

- One short note for `research/notes.md`: `<summary>`
- Any do-not-repeat update: `<summary or none>`
"""


def write_note(path: Path, state: dict[str, object], overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return
    path.write_text(build_note(state), encoding="utf-8")


def create_command(args: argparse.Namespace) -> int:
    experiment_id = ensure_id("experiment_id", args.experiment_id)
    worker_id = ensure_id("worker_id", args.worker_id or experiment_id)
    note_path = experiment_note_path(experiment_id)
    log_path = experiment_log_path(experiment_id)
    worktree = worktree_path(experiment_id)
    ensure_worktree(worktree)
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    master = load_master_snapshot()
    title = args.title or args.hypothesis
    state = {
        "experiment_id": experiment_id,
        "campaign": args.campaign,
        "hypothesis": args.hypothesis,
        "worker_id": worker_id,
        "title": title,
        "master_hash": master.get("hash"),
        "master_val_bpb": master.get("val_bpb"),
        "note_path": str(note_path),
        "log_path": str(log_path),
        "worktree_path": str(worktree),
        "created_at": utc_now(),
    }
    write_note(note_path, state, overwrite=args.overwrite_note)
    state_path = write_state(state)

    run_command = ["uv", "run", "scripts/opencode_worker.py", "run", experiment_id]
    print(json.dumps(state, indent=2, sort_keys=True))
    print(f"state: {state_path}")
    print(f"run: {' '.join(shlex.quote(part) for part in run_command)}")
    return 0


def build_prompt(state: dict[str, object]) -> str:
    return f"""You are executing one isolated Autolab experiment in this worktree.

Campaign: {state["campaign"]}
Experiment id: {state["experiment_id"]}
Worker id: {state["worker_id"]}
Hypothesis: {state["hypothesis"]}
Reserved log path: {state["log_path"]}
Durable note path in the main checkout: {state["note_path"]}

Read `AGENTS.md` first, then follow the repo rules exactly.

Execution contract:
- refresh current local master with `uv run scripts/refresh_master.py --fetch-dag` unless the worktree is already refreshed for this hypothesis
- edit `train.py` only unless explicitly authorized otherwise
- never edit `prepare.py`
- make exactly one hypothesis change
- run `uv run scripts/hf_job.py preflight`
- run exactly one managed experiment with `uv run scripts/hf_job.py launch --mode experiment`
- stream logs to `{state["log_path"]}`
- parse the final metric with `uv run scripts/parse_metric.py {state["log_path"]}`
- record the run with `uv run scripts/submit_patch.py --comment "..."`
- promotion is local and only happens if local `val_bpb` beats current master

Do not edit the durable note in the main checkout from this worktree. In your final response, include the note text that `memory-keeper` should record.
"""


def run_command_for_worker(args: argparse.Namespace) -> int:
    state = load_state(args.experiment_id)
    opencode_bin = args.opencode_bin or os.environ.get("AUTOLAB_OPENCODE_BIN") or require_tool("opencode")
    worktree = Path(str(state["worktree_path"]))
    if not worktree.exists():
        raise SystemExit(f"missing worktree: {worktree}")

    prompt = build_prompt(state)
    env = os.environ.copy()
    env["AUTOLAB_CAMPAIGN"] = str(state["campaign"])
    env["AUTOLAB_EXPERIMENT_ID"] = str(state["experiment_id"])
    env["AUTOLAB_WORKER_ID"] = str(state["worker_id"])
    env["AUTOLAB_HYPOTHESIS"] = str(state["hypothesis"])
    env["AUTOLAB_LOG_PATH"] = str(state["log_path"])
    env["AUTOLAB_EXPERIMENT_NOTE"] = str(state["note_path"])

    argv = [opencode_bin, "run", "--agent", "experiment-worker", prompt]
    if args.dry_run:
        print("cwd:", worktree)
        print("command:", " ".join(shlex.quote(part) for part in argv))
        for key in ("AUTOLAB_CAMPAIGN", "AUTOLAB_EXPERIMENT_ID", "AUTOLAB_WORKER_ID", "AUTOLAB_HYPOTHESIS", "AUTOLAB_LOG_PATH"):
            print(f"{key}={env[key]}")
        return 0

    result = subprocess.run(argv, cwd=worktree, env=env, check=False)
    return result.returncode


def cleanup_command(args: argparse.Namespace) -> int:
    state = load_state(args.experiment_id)
    worktree = Path(str(state["worktree_path"]))
    state_path = worker_state_path(args.experiment_id)
    if worktree.exists():
        status = run(["git", "status", "--short"], cwd=worktree)
        if status.returncode != 0:
            raise SystemExit(status.stderr.strip() or status.stdout.strip() or f"git status failed in {worktree}")
        if status.stdout.strip() and not args.force:
            raise SystemExit(f"worktree has uncommitted changes: {worktree}\npass --force to remove it anyway")
        argv = ["git", "worktree", "remove", str(worktree)]
        if args.force:
            argv.append("--force")
        result = run(argv)
        if result.returncode != 0:
            raise SystemExit(result.stderr.strip() or result.stdout.strip() or "git worktree remove failed")
    if state_path.exists():
        state_path.unlink()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create, run, and clean isolated OpenCode Autolab experiment workers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create an isolated worktree, state file, note, and reserved log path")
    create.add_argument("experiment_id", help="stable experiment identifier used for the worktree, note, and log")
    create.add_argument("--campaign", required=True, help="campaign name for this experiment")
    create.add_argument("--hypothesis", required=True, help="one-sentence experiment hypothesis")
    create.add_argument("--worker-id", help="logical worker id; defaults to the experiment id")
    create.add_argument("--title", help="note title; defaults to the hypothesis")
    create.add_argument("--overwrite-note", action="store_true", help="replace an existing experiment note")

    run_worker = subparsers.add_parser("run", help="run the isolated experiment worker through OpenCode")
    run_worker.add_argument("experiment_id", help="experiment id created by the `create` command")
    run_worker.add_argument("--opencode-bin", help="override the OpenCode executable")
    run_worker.add_argument("--dry-run", action="store_true", help="print the exact command and environment without running OpenCode")

    cleanup = subparsers.add_parser("cleanup", help="remove a finished worktree and its local worker state")
    cleanup.add_argument("experiment_id", help="experiment id created by the `create` command")
    cleanup.add_argument("--force", action="store_true", help="remove the worktree even when it still has local changes")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        return create_command(args)
    if args.command == "run":
        return run_command_for_worker(args)
    if args.command == "cleanup":
        return cleanup_command(args)
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

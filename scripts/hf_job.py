#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / ".runtime"
DEFAULT_BUNDLE = RUNTIME_DIR / "autolab-hf-job.py"
LAST_JOB_PATH = RUNTIME_DIR / "hf-job-last.json"
AUTOLAB_HOME = "/autolab-home"
AUTOLAB_CACHE_MOUNT = f"{AUTOLAB_HOME}/.cache/autoresearch"
SUMMARY_KEYS = {
    "val_bpb",
    "training_seconds",
    "total_seconds",
    "peak_vram_mb",
    "mfu_percent",
    "total_tokens_M",
    "num_steps",
    "num_params_M",
    "depth",
}
PREPARE_DEPENDENCIES = {
    "pyarrow",
    "requests",
    "rustbpe",
    "tiktoken",
    "torch",
}


def load_pyproject() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(f"{key} = {toml_value(val)}" for key, val in value.items())
        return "{ " + items + " }"
    raise TypeError(f"unsupported TOML value: {value!r}")


def dependency_name(spec: str) -> str:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", spec)
    if not match:
        raise ValueError(f"unable to parse dependency name from {spec!r}")
    return match.group(1).lower().replace("_", "-")


def build_pep723_header(mode: str) -> str:
    pyproject = load_pyproject()
    project = pyproject.get("project", {})
    tool = pyproject.get("tool", {})
    uv_tool = tool.get("uv", {}) if isinstance(tool, dict) else {}
    project_dependencies = list(project.get("dependencies", []))
    sources = uv_tool.get("sources", {}) if isinstance(uv_tool, dict) else {}
    indexes = uv_tool.get("index", []) if isinstance(uv_tool, dict) else []

    if mode == "prepare":
        dependencies = [
            dependency
            for dependency in project_dependencies
            if dependency_name(dependency) in PREPARE_DEPENDENCIES
        ]
        missing = PREPARE_DEPENDENCIES - {dependency_name(dep) for dep in dependencies}
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise RuntimeError(f"prepare dependency set missing from pyproject: {missing_list}")
        # Prepare runs on CPU and only needs data/tokenizer tooling, not CUDA wheels.
        sources = {}
        indexes = []
    else:
        dependencies = project_dependencies

    lines: list[str] = [
        f'requires-python = {toml_value(project.get("requires-python", ">=3.10"))}',
        "dependencies = [",
    ]
    for dependency in dependencies:
        lines.append(f"  {toml_value(dependency)},")
    lines.append("]")

    if sources:
        lines.append("")
        lines.append("[tool.uv.sources]")
        for package, source_value in sources.items():
            lines.append(f"{package} = {toml_value(source_value)}")

    if indexes:
        for index in indexes:
            lines.append("")
            lines.append("[[tool.uv.index]]")
            for key, value in index.items():
                lines.append(f"{key} = {toml_value(value)}")

    header = ["# /// script"]
    for line in lines:
        header.append("#" if not line else f"# {line}")
    header.append("# ///")
    return "\n".join(header)


def encode_text(path: Path) -> str:
    return base64.b64encode(path.read_text().encode("utf-8")).decode("ascii")


def build_smoke_script() -> str:
    return """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


if os.environ.get("AUTOLAB_HOME"):
    os.environ["HOME"] = os.environ["AUTOLAB_HOME"]

cache_root = Path.home() / ".cache" / "autoresearch"
cache_root.mkdir(parents=True, exist_ok=True)
job_id = os.environ.get("JOB_ID", "local")
artifact_dir = cache_root / "runs" / job_id
artifact_dir.mkdir(parents=True, exist_ok=True)

payload = {
    "job_id": job_id,
    "home": str(Path.home()),
    "cache_root": str(cache_root),
    "artifact_dir": str(artifact_dir),
    "entries": sorted(path.name for path in cache_root.iterdir())[:20],
}

(artifact_dir / "smoke.json").write_text(json.dumps(payload, indent=2) + "\\n")
print(json.dumps(payload, indent=2))
"""


def build_managed_script(mode: str) -> str:
    header = build_pep723_header(mode)
    prepare_payload = encode_text(ROOT / "prepare.py")
    train_payload = encode_text(ROOT / "train.py")
    return f"""#!/usr/bin/env python3
{header}
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path


SUMMARY_KEYS = {sorted(SUMMARY_KEYS)!r}
MODE = {mode!r}
FILES = {{
    "prepare.py": {prepare_payload!r},
    "train.py": {train_payload!r},
}}


def parse_metrics(text: str) -> dict[str, int | float | str] | None:
    metrics: dict[str, int | float | str] = {{}}
    for line in text.splitlines():
        match = re.match(r"^([a-z_]+):\\s+(.+)$", line.strip())
        if not match:
            continue
        key, raw = match.groups()
        if key not in SUMMARY_KEYS:
            continue
        value: int | float | str = raw
        for caster in (int, float):
            try:
                value = caster(raw)
                break
            except ValueError:
                continue
        metrics[key] = value
    return metrics if "val_bpb" in metrics else None


def apply_home_override() -> Path:
    autolab_home = os.environ.get("AUTOLAB_HOME")
    if autolab_home:
        os.environ["HOME"] = autolab_home
    cache_root = Path.home() / ".cache" / "autoresearch"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def hydrate_workspace(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for name, payload in FILES.items():
        target = workdir / name
        target.write_text(base64.b64decode(payload).decode("utf-8"))


def cache_missing(cache_root: Path) -> list[str]:
    missing: list[str] = []
    tokenizer_dir = cache_root / "tokenizer"
    data_dir = cache_root / "data"
    if not (tokenizer_dir / "tokenizer.pkl").exists():
        missing.append("tokenizer/tokenizer.pkl")
    if not (tokenizer_dir / "token_bytes.pt").exists():
        missing.append("tokenizer/token_bytes.pt")
    val_shard = data_dir / "shard_06542.parquet"
    if not val_shard.exists():
        missing.append("data/shard_06542.parquet")
    train_ready = False
    if data_dir.exists():
        train_ready = any(path.name != "shard_06542.parquet" for path in data_dir.glob("shard_*.parquet"))
    if not train_ready:
        missing.append("data/<train-shard>")
    return missing


def run_logged(argv: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            handle.write(line)
    return proc.wait()


def main() -> int:
    cache_root = apply_home_override()
    job_id = os.environ.get("JOB_ID", "local")
    artifact_dir = cache_root / "runs" / job_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    workdir = Path(os.environ.get("AUTOLAB_JOB_WORKDIR", f"/tmp/autolab-{{job_id}}"))
    hydrate_workspace(workdir)

    manifest = {{
        "job_id": job_id,
        "mode": MODE,
        "home": str(Path.home()),
        "cache_root": str(cache_root),
        "artifact_dir": str(artifact_dir),
        "workdir": str(workdir),
    }}
    (artifact_dir / "job-manifest.json").write_text(json.dumps(manifest, indent=2) + "\\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(workdir)
    env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    env.pop("AUTOLAB_FORCE_FA3_REDIRECT", None)

    if MODE == "prepare":
        log_path = artifact_dir / "prepare.log"
        rc = run_logged([sys.executable, "prepare.py"], cwd=workdir, env=env, log_path=log_path)
        if rc != 0:
            return rc
        missing = cache_missing(cache_root)
        if missing:
            print("Autolab cache bootstrap incomplete: " + ", ".join(missing), file=sys.stderr)
            return 2
        print(f"Prepared cache at {{cache_root}}")
        return 0

    missing = cache_missing(cache_root)
    if missing:
        print("Autolab cache missing: " + ", ".join(missing), file=sys.stderr)
        print("Run `python3 scripts/hf_job.py launch --mode prepare` first.", file=sys.stderr)
        return 2

    log_path = artifact_dir / "autolab-run.log"
    rc = run_logged([sys.executable, "train.py"], cwd=workdir, env=env, log_path=log_path)
    log_text = log_path.read_text(encoding="utf-8")
    metrics = parse_metrics(log_text)
    (artifact_dir / "train.py").write_text((workdir / "train.py").read_text(encoding="utf-8"))
    if metrics is None:
        print(f"val_bpb not found in {{log_path}}", file=sys.stderr)
        return rc or 3
    (artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\\n")
    print(json.dumps({{"job_id": job_id, "artifact_dir": str(artifact_dir), "metrics": metrics}}, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
"""


def render_bundle(mode: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "smoke":
        script_text = build_smoke_script()
    elif mode in {"prepare", "experiment"}:
        script_text = build_managed_script(mode)
    else:
        raise SystemExit(f"unsupported mode: {mode}")
    output_path.write_text(script_text, encoding="utf-8")
    return output_path


def parse_metrics(text: str) -> dict[str, int | float | str] | None:
    metrics: dict[str, int | float | str] = {}
    for line in text.splitlines():
        match = re.match(r"^([a-z_]+):\s+(.+)$", line.strip())
        if not match:
            continue
        key, raw = match.groups()
        if key not in SUMMARY_KEYS:
            continue
        value: int | float | str = raw
        for caster in (int, float):
            try:
                value = caster(raw)
                break
            except ValueError:
                continue
        metrics[key] = value
    return metrics if "val_bpb" in metrics else None


def resolve_bucket(explicit: str | None) -> str | None:
    return explicit or os.environ.get("AUTOLAB_HF_BUCKET")


def default_flavor(mode: str) -> str:
    env_map = {
        "smoke": os.environ.get("AUTOLAB_HF_SMOKE_FLAVOR"),
        "prepare": os.environ.get("AUTOLAB_HF_PREPARE_FLAVOR"),
        "experiment": os.environ.get("AUTOLAB_HF_EXPERIMENT_FLAVOR") or os.environ.get("AUTOLAB_HF_FLAVOR"),
    }
    fallback = {
        "smoke": "cpu-basic",
        "prepare": "cpu-performance",
        "experiment": "h200",
    }
    return env_map.get(mode) or fallback[mode]


def default_timeout(mode: str) -> str:
    env_map = {
        "smoke": os.environ.get("AUTOLAB_HF_SMOKE_TIMEOUT"),
        "prepare": os.environ.get("AUTOLAB_HF_PREPARE_TIMEOUT"),
        "experiment": os.environ.get("AUTOLAB_HF_EXPERIMENT_TIMEOUT") or os.environ.get("AUTOLAB_HF_TIMEOUT"),
    }
    fallback = {
        "smoke": "10m",
        "prepare": "2h",
        "experiment": "90m",
    }
    return env_map.get(mode) or fallback[mode]


def build_job_labels(mode: str) -> list[str]:
    labels = [
        "autolab",
        f"mode={mode}",
        "launcher=hf-job-py",
    ]
    master_json = ROOT / "research" / "live" / "master.json"
    if master_json.exists():
        try:
            master_hash = json.loads(master_json.read_text()).get("hash")
        except json.JSONDecodeError:
            master_hash = None
        if isinstance(master_hash, str) and master_hash:
            labels.append(f"master={master_hash[:12]}")
    return labels


def parse_job_id(text: str) -> str | None:
    matches = re.findall(r"\b[0-9a-f]{24}\b", text)
    return matches[-1] if matches else None


def run_command(argv: list[str], capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("HF_HUB_DISABLE_EXPERIMENTAL_WARNING", "1")
    return subprocess.run(argv, text=True, capture_output=capture_output, check=False, env=env)


def resolve_hf_cli() -> str:
    explicit = os.environ.get("AUTOLAB_HF_CLI")
    if explicit:
        return explicit
    preferred = Path.home() / ".local" / "bin" / "hf"
    if preferred.exists():
        return str(preferred)
    fallback = shutil.which("hf")
    if fallback:
        return fallback
    raise SystemExit("could not find `hf`; install the Hugging Face CLI first")


def ensure_bucket(bucket: str) -> None:
    argv = [resolve_hf_cli(), "buckets", "create", bucket, "--private", "--exist-ok"]
    result = run_command(argv, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def launch_job(args: argparse.Namespace) -> int:
    bucket = resolve_bucket(args.bucket)
    if args.mode in {"prepare", "experiment"} and not bucket:
        raise SystemExit("AUTOLAB_HF_BUCKET is required for prepare and experiment jobs")

    bundle_path = render_bundle(args.mode, args.output)
    flavor = args.flavor or default_flavor(args.mode)
    timeout = args.timeout or default_timeout(args.mode)
    hf_cli = resolve_hf_cli()

    if bucket and not args.skip_bucket_create:
        ensure_bucket(bucket)

    command = [hf_cli, "jobs", "uv", "run", "--flavor", flavor, "--timeout", timeout]
    if args.namespace:
        command.extend(["--namespace", args.namespace])
    if args.detach:
        command.append("--detach")
    for label in build_job_labels(args.mode) + args.label:
        command.extend(["--label", label])
    for env_entry in args.env:
        command.extend(["--env", env_entry])
    if bucket:
        command.extend(["--env", f"AUTOLAB_HOME={AUTOLAB_HOME}"])
        command.extend(["--volume", f"hf://buckets/{bucket}:{AUTOLAB_CACHE_MOUNT}"])
    command.append(str(bundle_path))

    print("Launching HF Job:")
    print("  " + " ".join(shlex.quote(part) for part in command))
    result = run_command(command, capture_output=True)
    combined_output = (result.stdout or "") + (result.stderr or "")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        return result.returncode

    state = {
        "mode": args.mode,
        "bundle_path": str(bundle_path),
        "bucket": bucket,
        "flavor": flavor,
        "hf_cli": hf_cli,
        "timeout": timeout,
        "command": command,
    }
    job_id = parse_job_id(combined_output)
    if job_id:
        state["job_id"] = job_id
    if args.namespace:
        state["namespace"] = args.namespace
    LAST_JOB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_JOB_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


def resolve_job_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    if LAST_JOB_PATH.exists():
        data = json.loads(LAST_JOB_PATH.read_text(encoding="utf-8"))
        job_id = data.get("job_id")
        if isinstance(job_id, str) and job_id:
            return job_id
    raise SystemExit("job id required; pass one explicitly or launch a job first")


def stream_logs(args: argparse.Namespace) -> int:
    job_id = resolve_job_id(args.job_id)
    argv = [resolve_hf_cli(), "jobs", "logs"]
    if args.follow:
        argv.append("--follow")
    if args.tail is not None:
        argv.extend(["--tail", str(args.tail)])
    if args.namespace:
        argv.extend(["--namespace", args.namespace])
    argv.append(job_id)

    output_handle = None
    collected: list[str] = []
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            output_handle = args.output.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            argv,
            env={**os.environ, "HF_HUB_DISABLE_EXPERIMENTAL_WARNING": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            collected.append(line)
            if output_handle is not None:
                output_handle.write(line)
        rc = proc.wait()
    finally:
        if output_handle is not None:
            output_handle.close()

    metrics = parse_metrics("".join(collected))
    if metrics is not None:
        print(json.dumps({"job_id": job_id, "metrics": metrics}, indent=2, sort_keys=True))
    return rc


def inspect_job(args: argparse.Namespace) -> int:
    job_id = resolve_job_id(args.job_id)
    argv = [resolve_hf_cli(), "jobs", "inspect"]
    if args.namespace:
        argv.extend(["--namespace", args.namespace])
    argv.append(job_id)
    result = run_command(argv, capture_output=False)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Autolab benchmark jobs on Hugging Face Jobs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="render the self-contained HF Jobs script")
    render_parser.add_argument("--mode", choices=("smoke", "prepare", "experiment"), default="experiment")
    render_parser.add_argument("--output", type=Path, default=DEFAULT_BUNDLE)

    launch_parser = subparsers.add_parser("launch", help="render and submit an HF Job")
    launch_parser.add_argument("--mode", choices=("smoke", "prepare", "experiment"), default="experiment")
    launch_parser.add_argument("--output", type=Path, default=DEFAULT_BUNDLE)
    launch_parser.add_argument("--bucket", help="HF bucket to mount at ~/.cache/autoresearch")
    launch_parser.add_argument("--flavor", help="override HF Jobs flavor")
    launch_parser.add_argument("--timeout", help="override HF Jobs timeout")
    launch_parser.add_argument("--namespace", help="run the job under this namespace")
    launch_parser.add_argument("--env", action="append", default=[], help="extra HF Jobs --env entries")
    launch_parser.add_argument("--label", action="append", default=[], help="extra HF Jobs --label entries")
    launch_parser.add_argument("--skip-bucket-create", action="store_true", help="do not create the bucket before launch")
    launch_parser.set_defaults(detach=True)
    detach_group = launch_parser.add_mutually_exclusive_group()
    detach_group.add_argument("--detach", dest="detach", action="store_true", help="submit in background (default)")
    detach_group.add_argument("--no-detach", dest="detach", action="store_false", help="stream logs during submission")

    logs_parser = subparsers.add_parser("logs", help="stream or fetch HF Jobs logs")
    logs_parser.add_argument("job_id", nargs="?", help="HF job id; defaults to the last launched job")
    logs_parser.add_argument("--follow", action="store_true", help="stream until completion")
    logs_parser.add_argument("--tail", type=int, help="only fetch the last N lines")
    logs_parser.add_argument("--output", type=Path, help="write logs to this file while streaming")
    logs_parser.add_argument("--namespace", help="namespace that owns the job")

    inspect_parser = subparsers.add_parser("inspect", help="inspect HF Job status")
    inspect_parser.add_argument("job_id", nargs="?", help="HF job id; defaults to the last launched job")
    inspect_parser.add_argument("--namespace", help="namespace that owns the job")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "render":
        path = render_bundle(args.mode, args.output)
        print(path)
        return 0
    if args.command == "launch":
        return launch_job(args)
    if args.command == "logs":
        return stream_logs(args)
    if args.command == "inspect":
        return inspect_job(args)
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

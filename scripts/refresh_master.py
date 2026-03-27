#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_DIR = ROOT / "research" / "live"
DEFAULT_HTTP_TIMEOUT = float(os.environ.get("AUTOLAB_HTTP_TIMEOUT", "10"))
DEFAULT_HTTP_RETRIES = int(os.environ.get("AUTOLAB_HTTP_RETRIES", "2"))


def load_autolab_base() -> str:
    base = os.environ.get("AUTOLAB")
    creds_path = Path.home() / ".autolab" / "credentials"
    if not base and creds_path.exists():
        for line in creds_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "AUTOLAB":
                base = value
                break
    return base or "http://autoresearchhub.com"


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    retries: int = DEFAULT_HTTP_RETRIES,
) -> dict | list:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").strip()
            detail = f" HTTP {exc.code}"
            if body:
                detail += f": {body}"
            raise SystemExit(f"failed to fetch {url}:{detail}") from exc
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < retries:
                print(
                    f"warning: fetch attempt {attempt}/{retries} failed for {url}: {exc}",
                    file=sys.stderr,
                )
    raise SystemExit(f"failed to fetch {url}: {last_error}") from last_error


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def detail_hash(detail: object) -> str | None:
    if not isinstance(detail, dict):
        return None
    commit = detail.get("commit")
    if isinstance(commit, dict):
        hash_value = commit.get("hash")
        if isinstance(hash_value, str):
            return hash_value
    hash_value = detail.get("hash")
    if isinstance(hash_value, str):
        return hash_value
    return None


def load_cached_detail(master_hash: str) -> dict | None:
    cached = load_json(LIVE_DIR / "master_detail.json")
    if not isinstance(cached, dict):
        return None
    if detail_hash(cached) != master_hash:
        return None
    if not isinstance(cached.get("source"), str):
        return None
    return cached


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def train_files_diverged() -> bool:
    train_path = ROOT / "train.py"
    train_orig_path = ROOT / "train_orig.py"
    if not train_path.exists() or not train_orig_path.exists():
        return False
    return train_path.read_text() != train_orig_path.read_text()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh train.py and train_orig.py from the current autolab master."
    )
    parser.add_argument(
        "--fetch-dag",
        action="store_true",
        help="also refresh research/live/dag.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite local train.py even if it diverged from train_orig.py",
    )
    args = parser.parse_args()

    if train_files_diverged() and not args.force:
        raise SystemExit(
            "train.py differs from train_orig.py; use --force if you really want to overwrite it"
        )

    base = load_autolab_base().rstrip("/")
    master = fetch_json(f"{base}/api/git/master")
    if not isinstance(master, dict) or "hash" not in master:
        raise SystemExit("master response was missing hash")

    detail_url = f"{base}/api/git/commits/{master['hash']}"
    try:
        detail = fetch_json(detail_url)
    except SystemExit as exc:
        cached_detail = load_cached_detail(master["hash"])
        if cached_detail is None:
            raise
        print(
            "warning: commit detail fetch failed; using cached "
            f"{(LIVE_DIR / 'master_detail.json').relative_to(ROOT)} for {master['hash']}: {exc}",
            file=sys.stderr,
        )
        detail = cached_detail
    if not isinstance(detail, dict) or "source" not in detail:
        raise SystemExit("commit detail response was missing source")

    write_json(LIVE_DIR / "master.json", master)
    write_json(LIVE_DIR / "master_detail.json", detail)

    if args.fetch_dag:
        dag = fetch_json(f"{base}/api/git/dag")
        write_json(LIVE_DIR / "dag.json", dag)

    source = detail["source"]
    if not isinstance(source, str):
        raise SystemExit("commit detail source was not a string")

    (ROOT / "train_orig.py").write_text(source)
    (ROOT / "train.py").write_text(source)

    val_bpb = master.get("val_bpb", "unknown")
    print(f"refreshed master {master['hash']} (val_bpb={val_bpb})")
    print(f"wrote {(ROOT / 'train.py').relative_to(ROOT)}")
    print(f"wrote {(ROOT / 'train_orig.py').relative_to(ROOT)}")
    print(f"wrote {(LIVE_DIR / 'master.json').relative_to(ROOT)}")
    print(f"wrote {(LIVE_DIR / 'master_detail.json').relative_to(ROOT)}")
    if args.fetch_dag:
        print(f"wrote {(LIVE_DIR / 'dag.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

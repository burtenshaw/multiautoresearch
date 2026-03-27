#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="install"

if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
  shift
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/install-rig-assets.sh [--check] [RIG_ROOT]

Copy the checked-in Gas Town autolab rig assets into a live Gas Town rig
container. Defaults to ~/gt/autolab.

Options:
  --check    verify that the live rig assets match this checkout without
             modifying the target
EOF
  exit 0
fi

TARGET_ROOT="${1:-$HOME/gt/autolab}"
PAIRS=(
  "$ROOT/gastown/directives/crew.md:$TARGET_ROOT/directives/crew.md"
  "$ROOT/gastown/directives/polecat.md:$TARGET_ROOT/directives/polecat.md"
  "$ROOT/gastown/formula-overlays/mol-polecat-work.toml:$TARGET_ROOT/formula-overlays/mol-polecat-work.toml"
  "$ROOT/gastown/templates/experiment-bead.md:$TARGET_ROOT/templates/experiment-bead.md"
  "$ROOT/gastown/templates/convoy-template.md:$TARGET_ROOT/templates/convoy-template.md"
  "$ROOT/gastown/taxonomy.md:$TARGET_ROOT/taxonomy.md"
  "$ROOT/gastown/convoys.md:$TARGET_ROOT/convoys.md"
  "$ROOT/gastown/day-1-checklist.md:$TARGET_ROOT/day-1-checklist.md"
  "$ROOT/docs/gastown-codex-guide.md:$TARGET_ROOT/instructions.md"
  "$ROOT/research/paper-ideas.md:$TARGET_ROOT/research/paper-ideas.md"
)

ensure_target_dirs() {
  mkdir -p \
    -- \
    "$TARGET_ROOT/directives" \
    "$TARGET_ROOT/formula-overlays" \
    "$TARGET_ROOT/research" \
    "$TARGET_ROOT/templates"
}

install_all() {
  local pair source target
  ensure_target_dirs
  for pair in "${PAIRS[@]}"; do
    source="${pair%%:*}"
    target="${pair#*:}"
    install -m 0644 "$source" "$target"
  done
  printf 'installed rig assets into %s\n' "$TARGET_ROOT"
}

check_all() {
  local pair source target status=0
  for pair in "${PAIRS[@]}"; do
    source="${pair%%:*}"
    target="${pair#*:}"
    if [[ ! -f "$target" ]]; then
      printf 'missing: %s\n' "$target" >&2
      status=1
      continue
    fi
    if ! cmp -s "$source" "$target"; then
      printf 'drift: %s\n' "$target" >&2
      status=1
    fi
  done
  if [[ "$status" -eq 0 ]]; then
    printf 'rig assets match %s\n' "$TARGET_ROOT"
  fi
  return "$status"
}

if [[ "$MODE" == "check" ]]; then
  check_all
else
  install_all
fi

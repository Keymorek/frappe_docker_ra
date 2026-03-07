#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() {
  printf '[codex] %s\n' "$*"
}

warn() {
  printf '[codex] warning: %s\n' "$*"
}

check_path() {
  local path="$1"
  if [[ -e "$path" ]]; then
    info "found $path"
  else
    warn "missing $path"
  fi
}

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    info "command available: $cmd"
  else
    warn "command not found: $cmd"
  fi
}

info "repo: $ROOT_DIR"
check_path "compose.yaml"
check_path "example.env"
check_path "devcontainer-example/docker-compose.yml"
check_path "development/installer.py"
check_path "custom_apps/fashion_erp"
check_path "docs/05-development/01-development.md"
check_path "docs/codex-environment.md"

if [[ -f .env ]]; then
  info "found .env"
else
  warn "missing .env"
  printf '  cp example.env .env\n'
fi

if [[ -f .devcontainer/docker-compose.yml ]]; then
  info "found .devcontainer/docker-compose.yml"
else
  warn "missing .devcontainer/docker-compose.yml"
  printf '  cp -R devcontainer-example .devcontainer\n'
fi

check_cmd "git"
check_cmd "docker"
check_cmd "python"

if command -v docker >/dev/null 2>&1; then
  docker --version || warn "unable to read docker version"
  docker compose version || warn "unable to read docker compose version"
fi

printf '\n'
info "recommended Codex setup script"
printf '  cd %s\n' "$ROOT_DIR"
printf '  bash scripts/codex-env-check.sh\n'

printf '\n'
info "recommended development workflow"
printf '  1. cp -R devcontainer-example .devcontainer\n'
printf '  2. docker compose -f .devcontainer/docker-compose.yml up -d\n'
printf '  3. docker compose -f .devcontainer/docker-compose.yml exec frappe bash\n'
printf '  4. cd /workspace && bash scripts/bootstrap-fashion-erp-dev.sh\n'
printf '  5. cd /workspace/development/frappe-bench && bench start\n'

printf '\n'
info "prod-like stack for image validation"
printf '  docker compose --env-file .env -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml up -d\n'
printf '\n'


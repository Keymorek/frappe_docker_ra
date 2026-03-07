#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PROJECT_DIR="${PROJECT_DIR:-$WORKSPACE_ROOT}"
DEV_DIR="${DEV_DIR:-$WORKSPACE_ROOT/development}"
BENCH_NAME="${BENCH_NAME:-frappe-bench}"
SITE_NAME="${SITE_NAME:-development.localhost}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-16}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
APPS_JSON="${APPS_JSON:-$PROJECT_DIR/scripts/apps-erpnext-v16.json}"
LOCAL_APP_SRC="${LOCAL_APP_SRC:-$PROJECT_DIR/custom_apps/fashion_erp}"
BENCH_DIR="$DEV_DIR/$BENCH_NAME"
SITE_DIR="$BENCH_DIR/sites/$SITE_NAME"
APP_LINK="$BENCH_DIR/apps/fashion_erp"

info() {
  printf '[bootstrap] %s\n' "$*"
}

die() {
  printf '[bootstrap] error: %s\n' "$*" >&2
  exit 1
}

require_path() {
  local path="$1"
  [[ -e "$path" ]] || die "missing $path"
}

require_path "$DEV_DIR/installer.py"
require_path "$APPS_JSON"
require_path "$LOCAL_APP_SRC"
command -v bench >/dev/null 2>&1 || die "bench is not available in PATH"

cd "$DEV_DIR"

if [[ ! -d "$BENCH_DIR" || ! -d "$SITE_DIR" ]]; then
  info "creating bench/site with ERPNext $FRAPPE_BRANCH"
  python installer.py \
    -j "$APPS_JSON" \
    -b "$BENCH_NAME" \
    -s "$SITE_NAME" \
    -t "$FRAPPE_BRANCH" \
    -a "$ADMIN_PASSWORD"
else
  info "bench and site already exist, skipping installer"
fi

require_path "$BENCH_DIR/env/bin/pip"

if [[ -L "$APP_LINK" ]]; then
  CURRENT_TARGET="$(readlink -f "$APP_LINK")"
  EXPECTED_TARGET="$(readlink -f "$LOCAL_APP_SRC")"
  [[ "$CURRENT_TARGET" == "$EXPECTED_TARGET" ]] || die "apps/fashion_erp points to $CURRENT_TARGET"
elif [[ -e "$APP_LINK" ]]; then
  CURRENT_TARGET="$(readlink -f "$APP_LINK")"
  EXPECTED_TARGET="$(readlink -f "$LOCAL_APP_SRC")"
  [[ "$CURRENT_TARGET" == "$EXPECTED_TARGET" ]] || die "apps/fashion_erp already exists at $CURRENT_TARGET"
else
  info "linking local fashion_erp source into bench"
  ln -s "$LOCAL_APP_SRC" "$APP_LINK"
fi

info "installing local app package into bench env"
"$BENCH_DIR/env/bin/pip" install -e "$APP_LINK"

cd "$BENCH_DIR"

if bench --site "$SITE_NAME" list-apps | grep -qx "fashion_erp"; then
  info "fashion_erp is already installed on $SITE_NAME"
else
  info "installing fashion_erp on $SITE_NAME"
  bench --site "$SITE_NAME" install-app fashion_erp
fi

info "running migrate/build/clear-cache"
bench --site "$SITE_NAME" migrate
bench build --app fashion_erp
bench --site "$SITE_NAME" clear-cache

printf '\n'
info "done"
printf '  cd %s\n' "$BENCH_DIR"
printf '  bench start\n'
printf '\n'


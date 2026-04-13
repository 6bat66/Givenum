#!/usr/bin/env bash

set -euo pipefail

export RESULTS_DIR="${RESULTS_DIR:-/app/results}"
export GIVENUM_ROOT_DIR="${GIVENUM_ROOT_DIR:-/app}"
export GIVENUM_CONFIG_DIR="${GIVENUM_CONFIG_DIR:-/root/.config/givenum}"
export GIVENUM_WEB_RUNTIME_DIR="${GIVENUM_WEB_RUNTIME_DIR:-/app/web-runtime}"

mkdir -p "$RESULTS_DIR" "$GIVENUM_CONFIG_DIR"

run_web() {
  if [ ! -f "$GIVENUM_WEB_RUNTIME_DIR/server.js" ]; then
    echo "[!] Missing built web runtime at $GIVENUM_WEB_RUNTIME_DIR" >&2
    exit 1
  fi

  cd "$GIVENUM_WEB_RUNTIME_DIR"
  exec node server.js "$@"
}

if [ $# -eq 0 ]; then
  run_web
fi

case "$1" in
  web|dashboard)
    shift
    run_web "$@"
    ;;
  scan)
    shift
    exec python3 /app/GivEnum.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac

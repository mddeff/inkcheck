#!/bin/sh
# Runs as root only long enough to make the data directory writable by the
# non-root app user (bind mounts arrive owned by the host user, often root),
# then drops privileges and execs the app as appuser.
set -e

DATA_DIR="$(dirname "${DATABASE_PATH:-/data/inkcheck.db}")"
mkdir -p "$DATA_DIR"
chown -R appuser:appuser "$DATA_DIR" 2>/dev/null || true

exec gosu appuser "$@"

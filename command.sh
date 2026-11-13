#!/usr/bin/env bash
# Compatibility entry for users of the first local version.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd)"
exec "$HERE/claude-zh" "$@"

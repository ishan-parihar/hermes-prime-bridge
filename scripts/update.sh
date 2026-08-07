#!/usr/bin/env bash
# Pull latest Prime Agent upstream into the vendor submodule, then re-pin.
set -euo pipefail
cd "$(dirname "$0")/.."
git submodule update --init --recursive
git -C vendor/prime-agent fetch origin main
git -C vendor/prime-agent checkout origin/main
git add vendor/prime-agent
echo "Upstream moved. Run tests, then commit."
echo "  now pinned at: $(git -C vendor/prime-agent rev-parse --short HEAD)"

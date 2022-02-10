#!/usr/bin/env bash

set -euxo pipefail

WORKERS=${WORKERS:-10}

find . -name "test_*.nix" | parallel -a - -j "${WORKERS}" --halt now,fail=1 nix-build --no-out-link --show-trace make-tests.nix --arg file

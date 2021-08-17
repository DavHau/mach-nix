#!/usr/bin/env sh

WORKERS=${WORKERS:-10}

ls ./test_* | parallel -a - -j $WORKERS --halt now,fail=1 nix-build --no-out-link --show-trace

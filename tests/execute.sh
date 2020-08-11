#!/usr/bin/env bash

for f in ./test_*.nix; do
  nix-build $f --no-out-link || exit 1
done

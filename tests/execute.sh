#!/usr/bin/env bash

ls ./test_* | parallel -a - -j 10 --halt now,fail=1 nix-build --show-trace

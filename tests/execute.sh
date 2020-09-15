#!/usr/bin/env bash

nix-build all-tests.nix --no-out-link --show-trace

#!/usr/bin/env bash
set -e
nix-shell -p nix-prefetch-git --run  "nix-prefetch-git --url https://github.com/davhau/pypi-deps-db --rev refs/heads/master  --no-deepClone" | python -m json.tool - PYPI_DEPS_DB.json
nix-shell -p nix-prefetch-git --run  "nix-prefetch-git --url https://github.com/nixos/nixpkgs --rev refs/heads/nixpkgs-unstable  --no-deepClone" | python -m json.tool - NIXPKGS.json

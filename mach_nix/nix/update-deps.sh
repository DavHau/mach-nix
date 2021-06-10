#!/usr/bin/env bash
set -e
nix-shell -p nix-prefetch-git --run  "nix-prefetch-git --url https://github.com/davhau/pypi-deps-db --rev refs/heads/master  --no-deepClone" | python -m json.tool - PYPI_DEPS_DB.json
nix-shell -p nix-prefetch-git --run  "nix-prefetch-git --url https://github.com/nixos/nixpkgs --rev refs/heads/nixpkgs-unstable  --no-deepClone" | python -m json.tool - NIXPKGS.json
nix-shell -p nix-prefetch-git --run  "nix-prefetch-git --url https://github.com/davhau/conda-channels --rev refs/heads/master  --no-deepClone" | python -m json.tool - CONDA_CHANNELS.json
jq --arg hash $(curl -L https://raw.githubusercontent.com/DavHau/conda-channels/master/sha256.json | sha256sum | awk '{ print $1 }') '. + {indexSha256: $hash}' CONDA_CHANNELS.json > C.json && mv C.json CONDA_CHANNELS.json

{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; },
  pypiData ? (import ./mach_nix/nix/deps-db-and-fetcher.nix {
    inherit pkgs;
  }).pypi_deps_db_src,
  chondaChannelsJson ? import ./mach_nix/nix/conda-channels.nix {
    providers = { _default = [ "conda/main" "conda/r" "conda/conda-forge"]; };
  },
  ...
}:
with pkgs;
let
  python = python38;
  machnixDeps = (lib.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = fetchurl; }));
in
mkShell {
  buildInputs = [
    (python.withPackages ( ps: with ps; machnixDeps ++ [ pytest_6 pytest-xdist twine ] ))
    nix-prefetch-git
    pkgs.parallel
  ];
  shellHook = ''
    export PYTHONPATH=$(pwd)/
    export PYPI_DATA=${pypiData}
    export CONDA_DATA=${chondaChannelsJson.condaChannelsJson}
    git config core.hooksPath ./git-hooks
  '';
}

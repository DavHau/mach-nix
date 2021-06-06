{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; },
  pypiData,
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
  ];
  shellHook = ''
    export PYTHONPATH=$(pwd)/
    export PYPI_DATA=${pypiData}
    git config core.hooksPath ./git-hooks
  '';
}

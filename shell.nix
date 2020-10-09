{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; },
  ...
}:
with pkgs;
let
  python = python37;
  machnixDeps = (lib.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = fetchurl; }));
in
mkShell {
  buildInputs = [
    (python.withPackages ( ps: with ps; machnixDeps ++ [ pytest_6 twine ] ))
    nix-prefetch-git
  ];
  shellHook = ''
    export PYTHONPATH=$(pwd)/
  '';
}

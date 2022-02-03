{
  pkgs ? import (import ./nixpkgs-src.nix) { config = {}; overlays = []; },
  dev ? false,
  extraModules ? [],
  ...
}:
let
  lib = pkgs.lib;
  python = pkgs.python39;
  pythonDeps = (lib.attrValues (import ./python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
  pythonDepsDev = with python.pkgs; [
    pytest_6
    pytest-xdist
  ];
in
python.withPackages ( ps:
  pythonDeps
  ++ (lib.optionals dev pythonDepsDev)
  ++ extraModules
)

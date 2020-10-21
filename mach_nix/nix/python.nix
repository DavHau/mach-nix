{
  pkgs ? import (import ./nixpkgs-src.nix) { config = {}; overlays = []; },
  ...
}:
with pkgs;
let
  python = python37;
  python_deps = (lib.attrValues (import ./python-deps.nix { inherit python; fetchurl = fetchurl; }));
in
python.withPackages ( ps: python_deps )

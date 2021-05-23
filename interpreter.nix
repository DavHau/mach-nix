# python interpreter for dev environment
let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; };
  python = pkgs.python38;
  deps = (pkgs.lib.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
in
python.withPackages (ps: deps ++ [
  ps.jupyterlab
])

let
  pkgs = import (import ../mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; };
  python = pkgs.python39;
  manylinux1 = [ pkgs.pythonManylinuxPackages.manylinux1 ];
  result = import ./overrides.nix { inherit pkgs python; };
  overrides = result.overrides manylinux1 pkgs.autoPatchelfHook;
  py = pkgs.python39.override { packageOverrides = overrides; };
in
py.withPackages (ps: result.select_pkgs ps)

let
  nixpkgs_commit = builtins.readFile ../mach_nix/nix/NIXPKGS_COMMIT;  # nixpkgs version to use python packages from
  nixpkgs_tarball_sha256 = builtins.readFile ../mach_nix/nix/NIXPKGS_SHA256;
  pkgs = import (builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${builtins.readFile ../mach_nix/nix/NIXPKGS_COMMIT}";
    sha256 = "${builtins.readFile ../mach_nix/nix/NIXPKGS_SHA256}";
  }) { config = {}; overlays = []; };
  python = pkgs.python37;
  manylinux1 = [ pkgs.pythonManylinuxPackages.manylinux1 ];
  result = import ./overrides.nix;
  overrides = result.overrides manylinux1 pkgs.autoPatchelfHook;
  py = pkgs.python37.override { packageOverrides = overrides; };
in
py.withPackages (ps: result.select_pkgs ps)

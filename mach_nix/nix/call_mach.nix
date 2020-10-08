{ requirements, python_attr , nixpkgs_rev , nixpkgs_sha }:
let
  nixpkgs = builtins.fetchTarball { 
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_rev}";
    sha256 = "${nixpkgs_sha}";
  };
  pkgs = import nixpkgs { config = {}; overlays = []; };
  python = pkgs."${python_attr}";
in

import ./mach.nix { inherit requirements pkgs python; }

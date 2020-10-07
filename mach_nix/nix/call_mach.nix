{ requirements, python_attr }:
let
  nixpkgs_src = builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${builtins.readFile ./NIXPKGS_COMMIT}";
    sha256 = "${builtins.readFile ./NIXPKGS_SHA256}";
  };
  pkgs = import nixpkgs_src { config = {}; overlays = []; };
  python = pkgs."${python_attr}";
in

import ./mach.nix { inherit requirements pkgs python; }

{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.pypi-deps-db = {
    url = "github:DavHau/pypi-deps-db";
    flake = false;
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.simpleFlake {
      inherit self nixpkgs;
      name = "mach-nix";
      overlay = ./overlay.nix;
      shell = ./shell.nix;
    } // {
      overlay = import ./overlay.nix;
    };
}

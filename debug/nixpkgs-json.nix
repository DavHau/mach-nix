let
  nixpkgs_src = (import ../mach_nix/nix/nixpkgs-src.nix).stable;
  python = (import nixpkgs_src { config = {}; }).python37;
in
with import nixpkgs_src { config = {}; };
import ../mach_nix/nix/nixpkgs-json.nix { inherit pkgs python; }
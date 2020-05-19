let
  nixpkgs_commit = builtins.readFile ../mach_nix/nix/NIXPKGS_COMMIT;  # nixpkgs version to use python packages from
  nixpkgs_tarball_sha256 = builtins.readFile ../mach_nix/nix/NIXPKGS_SHA256;
  target_nixpkgs_src = builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_commit}";
    sha256 = "${nixpkgs_tarball_sha256}";
  };
  #nixpkgs_src = (import ../mach_nix/nix/nixpkgs-src.nix).stable;
  python = (import target_nixpkgs_src { config = {}; }).python37;
in
with import target_nixpkgs_src { config = {}; overlays = []; };
import ../mach_nix/nix/nixpkgs-json.nix { inherit pkgs python; }
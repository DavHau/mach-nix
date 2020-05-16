let
  nixpkgs_commit = builtins.readFile ../mach_nix/nix/NIXPKGS_COMMIT;  # nixpkgs version to use python packages from
  nixpkgs_tarball_sha256 = builtins.readFile ../mach_nix/nix/NIXPKGS_SHA256;
  target_nixpkgs_src = builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_commit}";
    sha256 = "${nixpkgs_tarball_sha256}";
  };
  #nixpkgs_src = (import ../mach_nix/nix/nixpkgs-src.nix).stable;
  python = (import target_nixpkgs_src { config = {}; overlays = []; }).python37;
  overlay = import ./overlay.nix;
  custom = import ./custom_overlay.nix;
in
with import target_nixpkgs_src { config = {}; overlays = [ overlay custom ]; };
python37.withPackages (ps: machnix_python_pkgs ps)

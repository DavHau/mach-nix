let
  nixpkgsInput = (import ./flake-inputs.nix) "nixpkgs";
in
builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgsInput.rev}";
    sha256 = "${nixpkgsInput.sha256}";
}
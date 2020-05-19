builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${builtins.readFile ./NIXPKGS_COMMIT}";
    sha256 = "${builtins.readFile ./NIXPKGS_SHA256}";
}
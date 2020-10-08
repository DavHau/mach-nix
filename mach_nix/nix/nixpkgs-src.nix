let 
    nixpkgs_rev = builtins.fromJSON (builtins.readFile ./NIXPKGS.json);
in
builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_rev.rev}";
    sha256 = "${nixpkgs_rev.sha256}";
}
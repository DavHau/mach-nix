rec {
  stable = builtins.fetchTarball {
    name = "nixpkgs";
    # nixos-20.03
    url = "https://github.com/nixos/nixpkgs/tarball/b4db68ff563895eea6aab4ff24fa04ef403dfe14";
  };
}
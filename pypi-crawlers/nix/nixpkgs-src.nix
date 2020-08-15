rec {
  stable = builtins.fetchGit {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs-channels/";
    ref = "refs/heads/nixos-20.03";
    rev = "0a40a3999eb4d577418515da842a2622a64880c5";
  };
}
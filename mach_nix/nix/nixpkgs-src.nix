rec {
  stable = builtins.fetchGit {
    name = "nixos-19.09";
    url = "https://github.com/nixos/nixpkgs-channels/";
    # `git ls-remote https://github.com/nixos/nixpkgs-channels nixos-19.09`
    ref = "refs/heads/nixos-19.09";
    rev = "60c4ddb97fd5a730b93d759754c495e1fe8a3544";
  };
}
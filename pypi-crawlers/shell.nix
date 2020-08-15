let
  nixpkgs-src = (import ./nix/nixpkgs-src.nix).stable;
  pkgs = import nixpkgs-src {};
  env = ./env;
in
pkgs.mkShell {
  buildInputs = [
    (import ./nix/python.nix)
    pkgs.nixops
    pkgs.nix
  ];
  shellHook = ''
    export NIX_PATH="nixpkgs=${nixpkgs-src}:."
    export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt
    export PYTHONPATH=$(pwd)/src
    source ${env}
  '';
}

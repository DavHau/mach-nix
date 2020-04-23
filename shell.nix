with import (import ./mach_nix/nix/nixpkgs-src.nix).stable { config = {}; };
mkShell {
  buildInputs = [
    (import ./mach_nix/nix/python.nix { inherit pkgs; })
  ];
  shellHook = ''
    export PYTHONPATH=$(pwd)/
  '';
}

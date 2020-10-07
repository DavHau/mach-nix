with import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; };
mkShell {
  buildInputs = [
    (import ./mach_nix/nix/python.nix { inherit pkgs; })
    python37Packages.twine
  ];
  shellHook = ''
    export PYTHONPATH=$(pwd)/
  '';
}

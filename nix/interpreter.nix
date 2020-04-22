import ./python.nix {pkgs = import (import ./nixpkgs-src.nix).stable { config = {}; }; }

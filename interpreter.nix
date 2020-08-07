# python interpreter for dev environment
import ./mach_nix/nix/python.nix {
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; };
}

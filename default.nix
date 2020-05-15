let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix).stable { config = {}; };
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };
  python_deps = (pkgs.lib.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
in
rec {
  # the mach-nix cmdline tool derivation
  mach-nix = python.pkgs.buildPythonPackage rec {
    pname = "mach-nix";
    version = builtins.readFile ./mach_nix/VERSION;
    name = "${pname}-${version}";
    src = ./.;
    propagatedBuildInputs = python_deps;
    doCheck = false;
  };

  # call this to generate a nix expression defnining a python environment
  #mkPythonExpr = args: import ./mach_nix/nix/expression.nix args;

  # call this to generate a nixpkgs overlay .nix file which satisfies your requirements
  mkNixpkgsOverlayFile = args: import ./mach_nix/nix/expression.nix args;

  # call this to generate a nixpkgs overlay which satisfies your requirements
  mkNixpkgsOverlay = args: import "${mkNixpkgsOverlayFile args}/share/overlay.nix;

  # call this to generate a python environment
  mkPython =

  # call this to use the python environment with nix-shell
  mkPythonShell = args: (mkPython args).env;
}

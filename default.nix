let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix).stable { config = {}; };
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };
  python_deps = (pkgs.lib.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
in
python.pkgs.buildPythonPackage rec {
  pname = "mach-nix";
  version = builtins.readFile ./mach_nix/VERSION;
  name = "${pname}-${version}";
  src = ./.;
  propagatedBuildInputs = python_deps;
  doCheck = false;
}
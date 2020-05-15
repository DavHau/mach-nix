let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix).stable { config = {}; };
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };
  python_deps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
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
  mkOverlayFile = args: import ./mach_nix/nix/mk_overlay.nix args;

  # call this to generate a nixpkgs overlay which satisfies your requirements
  mkOverlay = args: import "${mkOverlayFile args}/share/overlay.nix";

  # call this to use the python environment with nix-shell
  mkPythonShell = args: (mkPython args).env;

  # call this to generate a python environment
  mkPython =
    {
      requirements,  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      nixpkgs_src ? builtins.fetchTarball {
        name = "nixpkgs";
        url = "https://github.com/nixos/nixpkgs/tarball/${builtins.readFile ./mach_nix/nix/NIXPKGS_COMMIT}";
        sha256 = "${builtins.readFile ./mach_nix/nix/NIXPKGS_SHA256}";
      },
      overlays_pre ? [],
      overlays_post ? [],
      providers ? "nixpkgs,sdist,wheel",
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python_attr ? "python3"
    }:
    let
      machnix_overlay = mkOverlay {
        inherit requirements disable_checks providers pypi_deps_db_commit pypi_deps_db_sha256;
        python = (import nixpkgs_src { config = {}; overlays = overlays_pre; })."${python_attr}";
      };
      pkgs = import nixpkgs_src {
        config = {};
        overlays = overlays_pre ++ [ machnix_overlay ] ++ overlays_post;
      };
    in
      pkgs."${python_attr}".withPackages (ps: pkgs.machnix_python_pkgs ps)
    ;
}

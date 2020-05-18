let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix).stable { config = {}; };
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };
  python_deps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
  mergeOverrides = with pkgs.lib; overrides:
    if length overrides == 0
    then a: b: {}  # return dummy overrides
    else
      if length overrides == 1
      then elemAt overrides 0
      else
        let
          last = head ( reverseList overrides );
          rest = reverseList (tail ( reverseList overrides ));
        in
          composeExtensions (mergeOverrides rest) last;
  machnix_nixpkgs = import (builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${builtins.readFile ./mach_nix/nix/NIXPKGS_COMMIT}";
    sha256 = "${builtins.readFile ./mach_nix/nix/NIXPKGS_SHA256}";
  }) { config = {}; overlays = []; };
  autoPatchelfHook = import ./mach_nix/nix/auto_patchelf_hook.nix {inherit (pkgs) fetchurl makeSetupHook writeText;};
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

  inherit mergeOverrides;

  # call this to generate a nix expression defnining a python environment
  #mkPythonExpr = args: import ./mach_nix/nix/expression.nix args;

  # call this to generate a nixpkgs overlay .nix file which satisfies your requirements
  mkOverridesFile = args: import ./mach_nix/nix/mach.nix args;

  # call this to generate a nixpkgs overlay which satisfies your requirements
  mkOverrides = args: import "${mkOverridesFile args}/share/mach_nix_file.nix";

  # call this to use the python environment with nix-shell
  mkPythonShell = args: (mkPython args).env;

  # call this to generate a python environment
  mkPython =
    {
      requirements,  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      overrides_pre ? [],  # list with pythonOverrides functions to apply before the amchnix overrides
      overrides_post ? [],  # list with pythonOverrides functions to apply after the amchnix overrides
      pkgs ? machnix_nixpkgs,  # pass custom nixpkgs version (20.03 or higher is recommended)
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3  # select custom python. It should be taken from `pkgs` passed above.
    }:
    let
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = mkOverrides {
        inherit requirements disable_checks providers pypi_deps_db_commit pypi_deps_db_sha256;
        python = py;
      };
      overrides_machnix = result.overrides pkgs.pythonManylinuxPackages.manylinux1 autoPatchelfHook;
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ [
          overrides_machnix
        ] ++ overrides_post
      );};
    in
      py_final.withPackages (ps: result.select_pkgs ps)
    ;
}

let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; };
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

  # User might want to access it to choose python version
  nixpkgs = pkgs;

  # call this to generate a nix expression which contains the python overrides
  machNixFile = args: import ./mach_nix/nix/mach.nix args;

  # Returns `overrides` and `select_pkgs` which satisfy your requirements
  machNix = args:
    let result = import "${machNixFile args}/share/mach_nix_file.nix";
    in {
      overrides = result.overrides pkgs.pythonManylinuxPackages.manylinux1 autoPatchelfHook;
      select_pkgs = result.select_pkgs;
    };

  # call this to use the python environment with nix-shell
  mkPythonShell = args: (mkPython args).env;

  # equivalent to buildPythonPackage of nixpkgs
  buildPythonPackage = _buildPython "buildPythonPackage";

  # equivalent to buildPythonApplication of nixpkgs
  buildPythonApplication = _buildPython "buildPythonApplication";

  _buildPython = func: args@{
      requirements,  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      dont_strip ? [], # list of libraries to not strip. Some libraries cannot be stripped twice (https://github.com/pypa/manylinux/issues/119)
      overrides_pre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overrides_post ? [],  # list of pythonOverrides to apply after the machnix overrides
      pkgs ? nixpkgs,  # pass custom nixpkgs. Only used for manylinux wheel dependencies
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3,  # select custom python to base overrides on. Should be from nixpkgs >= 20.03
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml),
      ...
    }:
    let
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit requirements disable_checks dont_strip providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        python = py;
      };
      py_final = python.override { packageOverrides = mergeOverrides (
          overrides_pre ++ [ result.overrides ] ++ overrides_post
        );};
      pass_args = removeAttrs args (builtins.attrNames ({inherit requirements disable_checks providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;}));
    in
    py_final.pkgs."${func}" ( pass_args // {
      propagatedBuildInputs = result.select_pkgs py_final.pkgs;
    });


  # (High level API) generates a python environment with minimal user effort
  mkPython =
    {
      requirements,  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      dont_strip ? [], # list of libraries to not strip. Some libraries cannot be stripped twice (https://github.com/pypa/manylinux/issues/119)
      overrides_pre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overrides_post ? [],  # list of pythonOverrides to apply after the machnix overrides
      pkgs ? nixpkgs,  # pass custom nixpkgs. Only used for manylinux wheel dependencies
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3,  # select custom python to base overrides on. Should be from nixpkgs >= 20.03
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml)
    }:
    let
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit requirements disable_checks dont_strip providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        python = py;
      };
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ [ result.overrides ] ++ overrides_post
      );};
    in
      py_final.withPackages (ps: result.select_pkgs ps)
    ;
}

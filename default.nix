{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; },
  pypiDataRev ? (builtins.fromJSON (builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB.json)).rev,
  pypiDataSha256 ? (builtins.fromJSON (builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB.json)).sha256,
  python ? "python3",
  ...
}:

with builtins;
with pkgs.lib;

let
  l = import ./mach_nix/nix/lib.nix { inherit pkgs; lib = pkgs.lib; };

  python_machnix = import ./mach_nix/nix/python.nix { inherit pkgs; };

  python_deps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix {
    python = python_machnix;
    fetchurl = pkgs.fetchurl;
  }));

  pypiFetcher = (import ./mach_nix/nix/deps-db-and-fetcher.nix {
    inherit pkgs;
    pypi_deps_db_commit = pypiDataRev;
    pypi_deps_db_sha256 = pypiDataSha256;
  }).pypi_fetcher;

  withDot = mkPython: import ./mach_nix/nix/withDot.nix { inherit mkPython pypiFetcher; };

  __buildPython = func: args: _buildPython func args;

  _buildPython = func: args:
    if args ? extra_pkgs || args ? pkgsExtra then
      throw "'extra_pkgs'/'pkgsExtra' cannot be passed to ${func}. Please pass it to a mkPython call."
    else if isString args || isPath args || pkgs.lib.isDerivation args then
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiDataRev pypiDataSha256; })
        python func { src = args; }
    else
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiDataRev pypiDataSha256; })
        python func (l.throwOnDeprecatedArgs func args);

  __mkPython = caller: args: _mkPython caller args;

  # (High level API) generates a python environment with minimal user effort
  _mkPython = caller: args:
    if builtins.isList args then
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiDataRev pypiDataSha256; })
        python { extra_pkgs = args; }
    else
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiDataRev pypiDataSha256; })
        python (l.throwOnDeprecatedArgs caller args);

  exposed = rec {
    # the main functions
    mkPython = args: __mkPython "mkPython" args;
    mkPythonShell = args: (__mkPython "mkPythonShell" args).env;
    mkDockerImage = args: (__mkPython "mkDockerImage" args).dockerImage;
    mkOverlay = args: (__mkPython "mkOverlay" args).overlay;
    mkNixpkgs = args: (__mkPython "mkNixpkgs" args).nixpkgs;
    mkPythonOverrides = args: (__mkPython "mkPythonOverrides" args).pythonOverrides;

    # equivalent to buildPythonPackage of nixpkgs
    buildPythonPackage = __buildPython "buildPythonPackage";

    # equivalent to buildPythonApplication of nixpkgs
    buildPythonApplication = __buildPython "buildPythonApplication";

    # provide pypi fetcher to user
    fetchPypiSdist = pypiFetcher.fetchPypiSdist;
    fetchPypiWheel = pypiFetcher.fetchPypiWheel;

    # expose mach-nix' nixpkgs
    # those are equivalent to the pkgs passed by the user
    nixpkgs = pkgs;

    # expose R packages
    rPackages = pkgs.rPackages;

    # this might beuseful for someone
    inherit (l) mergeOverrides;
  };

in
exposed // rec {
  # the mach-nix cmdline tool derivation
  mach-nix = python_machnix.pkgs.buildPythonPackage rec {
    pname = "mach-nix";
    version = builtins.readFile ./mach_nix/VERSION;
    name = "${pname}-${version}";
    src = ./.;
    propagatedBuildInputs = python_deps;
    checkInputs = [ python_machnix.pkgs.pytest ];
    checkPhase = "pytest";
  };

  inherit exposed;

  # expose dot interface for flakes cmdline
  "with" = (withDot (__mkPython "'.with'"))."with";
  pythonWith = (withDot (__mkPython "'.pythonWith'")).pythonWith;
  shellWith = (withDot (__mkPython "'.shellWith'")).shellWith;
  dockerImageWith = (withDot (__mkPython "'.dockerImageWith'")).dockerImageWith;
}

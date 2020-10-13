{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; },
  pypiDataRev ? (builtins.fromJSON (builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB.json)).rev,
  pypiDataSha256 ? (builtins.fromJSON (builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB.json)).sha256,
  ...
}:

with builtins;
with pkgs.lib;

let
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };

  python_deps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix {
    inherit python;
    fetchurl = pkgs.fetchurl;
  }));

  pypiFetcher = (import ./mach_nix/nix/deps-db-and-fetcher.nix {
    inherit pkgs;
    pypi_deps_db_commit = pypiDataRev;
    pypi_deps_db_sha256 = pypiDataSha256;
  }).pypi_fetcher;

  withDot = mkPython: import ./mach_nix/nix/withDot.nix { inherit mkPython pypiFetcher; };

  __buildPython = with builtins; func: args:
    if args ? pkgs then
      throw "${func} does not accept 'pkgs' anymore. 'pkgs' need to be specified when importing mach-nix"
    else if args ? extra_pkgs then
      throw "'extra_pkgs' cannot be passed to ${func}. Please pass it to a mkPython call."
    else if isString args || isPath args || pkgs.lib.isDerivation args then
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiDataRev pypiDataSha256; }) func { src = args; }
    else
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiDataRev pypiDataSha256; }) func args;

  # (High level API) generates a python environment with minimal user effort
  mkPythonBase = caller: args:
    if args ? pkgs then
      throw "${caller} does not accept 'pkgs' anymore. 'pkgs' need to be specified when importing mach-nix"
    else if builtins.isList args then
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiDataRev pypiDataSha256; }) { extra_pkgs = args; }
    else
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiDataRev pypiDataSha256; }) args;

in
rec {
  # the mach-nix cmdline tool derivation
  mach-nix = python.pkgs.buildPythonPackage rec {
    pname = "mach-nix";
    version = builtins.readFile ./mach_nix/VERSION;
    name = "${pname}-${version}";
    src = ./.;
    propagatedBuildInputs = python_deps;
    checkInputs = [ python.pkgs.pytest ];
    checkPhase = "pytest";
  };

  # the main functions
  mkPython = args: mkPythonBase "mkPython" args;
  mkPythonShell = args: (mkPythonBase "mkPythonShell" args).env;
  mkDockerImage = args: (mkPythonBase "mkDockerImage" args).dockerImage;
  mkOverlay = args: (mkPythonBase "mkOverlay" args).overlay;
  mkNixpkgs = args: (mkPythonBase "mkNixpkgs" args).nixpkgs;
  mkPythonOverrides = args: (mkPythonBase "mkPythonOverrides" args).pythonOverrides;

  # equivalent to buildPythonPackage of nixpkgs
  buildPythonPackage = __buildPython "buildPythonPackage";

  # equivalent to buildPythonApplication of nixpkgs
  buildPythonApplication = __buildPython "buildPythonApplication";

  # provide pypi fetcher to user
  fetchPypiSdist = pypiFetcher.fetchPypiSdist;
  fetchPypiWheel = pypiFetcher.fetchPypiWheel;

  # expose dot interface for flakes cmdline
  "with" = (withDot (mkPythonBase "'.with'"))."with";
  pythonWith = (withDot (mkPythonBase "'.pythonWith'")).pythonWith;
  shellWith = (withDot (mkPythonBase "'.shellWith'")).shellWith;
  dockerImageWith = (withDot (mkPythonBase "'.dockerImageWith'")).dockerImageWith;

  # expose mach-nix' nixpkgs
  # those are equivalent to the pkgs passed by the user
  nixpkgs = pkgs;

  # expose R packages
  rPackages = pkgs.rPackages;

  # this might beuseful for someone
  inherit mergeOverrides;
}

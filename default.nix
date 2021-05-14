{
  dataOutdated ? false,
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; },
  pypiData ? builtins.fetchTarball {
    name = "pypi-deps-db-src";
    url = "https://github.com/DavHau/pypi-deps-db/tarball/${pypiDataRev}";
    sha256 = "${pypiDataSha256}";
  },
  pypiDataRev ? ((import ./mach_nix/nix/flake-inputs.nix) "pypi-deps-db").rev,
  pypiDataSha256 ? ((import ./mach_nix/nix/flake-inputs.nix) "pypi-deps-db").sha256,
  python ? "python3",
  ...
}:

with builtins;
with pkgs.lib;

let
  l = import ./mach_nix/nix/lib.nix { inherit pkgs; lib = pkgs.lib; };

  python_machnix = import ./mach_nix/nix/python.nix { inherit pkgs; };

  pypiFetcher = (import ./mach_nix/nix/deps-db-and-fetcher.nix {
    inherit pkgs;
    deps_db_src = pypiData;
  }).pypi_fetcher;

  withDot = mkPython: import ./mach_nix/nix/withDot.nix { inherit mkPython pypiFetcher; };

  throwOnOutdatedData = args:
    if dataOutdated && ! (args.ignoreDataOutdated or false) then
      throw ''
        The pypiDataRev seems to be older than the nixpkgs which is currently used.
        Because of this, mach-nix might lack dependency information for some python packages in nixpkgs.
        This can degrade the quality of the generated environment or result in failing builds.
        It is recommended to pass a newer pypiDataRev to mach-nix during import.
        For flakes users: Update the `pypi-deps-db` input of mach-nix.
        You can ignore this error by passing 'ignoreDataOutdated = true' to mk* or build* functions
      ''
    else args;

  __buildPython = func: args: _buildPython func (throwOnOutdatedData args);

  _buildPython = func: args:
    if args ? extra_pkgs || args ? pkgsExtra then
      throw "'extra_pkgs'/'pkgsExtra' cannot be passed to ${func}. Please pass it to a mkPython call."
    else if isString args || isPath args || pkgs.lib.isDerivation args then
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiData; })
        python func { src = args; }
    else
      (import ./mach_nix/nix/buildPythonPackage.nix { inherit pkgs pypiData; })
        python func (l.throwOnDeprecatedArgs func args);

  __mkPython = caller: args: _mkPython caller (throwOnOutdatedData args);

  # (High level API) generates a python environment with minimal user effort
  _mkPython = caller: args:
    if builtins.isList args then
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiData; })
        python { packagesExtra = args; }
    else
      (import ./mach_nix/nix/mkPython.nix { inherit pkgs pypiData; })
        python (l.throwOnDeprecatedArgs caller args);

in
rec {
  # the mach-nix cmdline tool derivation
  mach-nix = python_machnix.pkgs.buildPythonApplication rec {
    pname = "mach-nix";
    version = builtins.readFile ./mach_nix/VERSION;
    name = "${pname}-${version}";
    src = ./.;
    propagatedBuildInputs = pythonDeps;
    checkInputs = [ python_machnix.pkgs.pytest ];
    checkPhase = "pytest";
  };

  pythonDeps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix {
    python = python_machnix;
    fetchurl = pkgs.fetchurl;
  }));

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

  # expose dot interface for flakes cmdline
  "with" = pythonWith;
  pythonWith = (withDot (__mkPython "'.pythonWith'")).pythonWith;
  shellWith = (withDot (__mkPython "'.shellWith'")).shellWith;
  dockerImageWith = (withDot (__mkPython "'.dockerImageWith'")).dockerImageWith;

  # expose mach-nix' nixpkgs
  # those are equivalent to the pkgs passed by the user
  nixpkgs = pkgs;

  # expose R packages
  rPackages = pkgs.rPackages;

  # this might beuseful for someone
  inherit (l) mergeOverrides;
}

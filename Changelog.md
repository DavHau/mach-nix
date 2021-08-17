# 3.3.0 (22 May 2021)
bugfixes, improvements

### Changes
 - The flakes cmdline api has been changed. New usage:
   ```
   nix (build|shell) mach-nix#gen.(python|docker).package1.package2...
   ```
   (Despite this change being backward incompatible, I did not bump the major version since everything flakes related should be considered experimental anyways)

### Improvements
 - Mach-nix (used via flakes) will now throw an error if the selected nixpkgs version is newer than the dependency DB since this can cause conflicts in the resulting environment.
 - When used via flakes, it was impossible to select the python version because the import function is not used anymore. Now `python` can be passed to `mkPython` alternatively.
 - For the flakes cmdline api, collisions are now ignored by default
 - The simplified override interface did not deal well with non-existent values. 
    - Now the `.add` directive automatically assumes an empty list/set/string when the attribute to be extended doesn't exist.
    - Now the `.mod` directive will pass `null` to the given function if the attribute to modify doesn't exist instead.

### Fixes
 - Generating an environment with a package named `overrides` failed due to a variable name collision in the resulting nix expression.
 - When used via flakes, the pypiData was downloaded twice, because the legacy code path for fetching was still used instead of the flakes input.
 - `nix flake show mach-nix` failed because it required IFD for foreign platforms.
 - For environments generated via `mach-nix env ...` the `python` command referred to the wrong interpreter.
 - When checking wheels for compatibility, the minor version for python was not respected which could lead to invalid environments.
 - Some python modules in nixpkgs propagate unnecessary dependencies which could lead to collisions in the final environment. Now mach-nix recursively removes all python dependencies which are not strictly required.

### Package Fixes
 - cryptography: remove rust related hook when version < 3.4



# 3.2.0 (11 Mar 2021)
bugfixes, ignoreCollisions

### Features
 - add argument `ignoreCollisions` to all `mk*` functions
 - add passthru attribute `expr` to the result of `mkPython`, which is a string containing the internally generated nix expression.
 - add flake output `sdist` to build pip compatible sdist distribution of mach-nix

### Fixes
 - Sometimes wrong package versions were inherited when using the `nixpkgs` provider, leading to collision errors or unexpected package versions. Now, python depenencies of `nixpkgs` candidates are automatically replaced recursively.
 - When cross building, mach-nix attempted to generate the nix expression using the target platform's python interpreter, resulting in failure

### Package Fixes
 - cartopy: add missing build inputs (geos)
 - google-auth: add missing dependency `six` when provider is `nixpkgs`


# 3.1.1 (27 Nov 2020)
fix cli

### Fixes
 - Fix missing flake.lock error when using mach-nix cli.


# 3.1.0 (27 Nov 2020)
flakes lib, cli improvements, bugfixes

### Features
 - expose the following functions via flakes `lib`:
    - mkPython / mkPythonShell / mkDockerImage / mkOverlay / mkNixpkgs / mkPythonOverrides
    - buildPythonPackage / buildPythonApplication
    - fetchPypiSdist / fetchPypiWheel
 - Properly manage and lock versions of `nixpkgs` and `mach-nix` for environments created via `mach-nix env` command.
 - Add example on how to use mach-nix with jupyterWith

### Improvements
 - Improve portability of `mach-nix env` generated environments. Replace the platform specific compiled nix expression with a call to mach-nix itself, which is platform agnostic.
 - Mach-nix now produces the same result no matter if it is used through flakes or legacy interface. The legacy interface now loads its dependencies via `flakes.lock`.

### Fixes
 - mkDockerImage produced corrupt images.
 - non-python packages passed via `packagesExtra` were not available during runtime. Now they are added to the `PATH`.
 - remove `<nixpkgs>` impurity in the dependency extractor used in buildPythonPackage.
 


# 3.0.2 (27 Oct 2020)
bugfixes

### Fixes
 - fixed "\u characters in JSON strings are currently not supported" error, triggered by some packages using unicode characters in their file names
 - mach-nix cmdline tool didn't use specified python version
 - wheel provider was broken for MacOS resulting in 0 available packages
 - several issues triggering infinite recursions


# 3.0.1 (21 Oct 2020)
bugfixes, return missing packages

### Fixes
 - Some sdist packages were missing from the dependency DB due to a corrupt index in the SQL DB used by the crawler.
 - When automatically fixing circular deps, removed deps could trigger a `No matching distribution found` error in higher level parent packages. Now `--no-dependencies` is set recursively for all parents of removed deps.
 - Mapping out the resulting dependency DAG to a tree for printing could exhaust the systems resources, due to complexity. Now, when printing dependencies, sub-trees are trimmed and marked via (...) if they have already been printed earlier.

### Improvements
 - optimized autoPatchelfHook for faster processing of large wheel packages (see [upstream PR](https://github.com/NixOS/nixpkgs/pull/101142))
 - `networkx` is now used for dealing with some graph related problems


# 3.0.0 (14 Oct 2020)
flakes pypi gateway, R support, new output formats, more packages for python 3.5/3.6, improved providers nixpkgs/wheel

### IMPORTANT NOTICE
The UI has been reworked. It is backward compatible with a few exceptions. Most importantly, when importing mach-nix, an attribute set must be passed. It can be empty. Example:
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/3.0.0";
  }) {
    # optionally bring your own nixpkgs
    # pkgs = import <nixpkgs> {};

    # or specify the python version
    # python = "python38";
  };
in
...
```

### Features
  - Flakes gateway to pypi. Get a nix shell with arbitrary python packages. Example:  
   `nix develop github:davhau/mach-nix#shellWith.requests.tensorflow.aiohttp`
- or a docker image  
  `nix build github:davhau/mach-nix#dockerImageWith.package1.package2 ...`
- or a python derivation  
  `nix build github:davhau/mach-nix#with.package1.package2 ...`
 - New output formats:  
   * **mkDockerImage** -> produces layered docker image containing a python environment  
   * **mkNixpkgs** -> returns nixpkgs which is conform to the given requirements   
   * **mkOverlay** -> returns an overlay function to make nixpkgs conform to the given requirements  
   * **mkPythonOverrides** -> produces pythonOverrides to make python conform to the given requirements.

 - New functions **fetchPypiSdist** and **fetchPypiWheel**. Example:
    ```
    mach-nix.buildPythonPackge {
      src = fetchPypiSdist "requests" "2.24.0"
    };
    ```

 - When using the mach-nix cmdline tool, the nixpkgs channel can now be picked via:
    ```
    mach-nix env ./env -r requirements.txt --nixpkgs nixos-20.09
    ```

 - R support (experimental): R packages can be passed via `packagesExtra`. Mach-nix will setup rpy2 accordingly. See [usage example](https://github.com/DavHau/mach-nix/blob/master/examples.md#r-and-python).
 
 - Non-python packages can be passed via `packagesExtra` to include them into the environment.
 
  the target platform's python interpreter was used to generate the nix expression, resulting in a failing build
### Improvements
 - rework the logic for inheriting dependencies from nixpkgs
 - fixes.nix: allow alternative mod function signature with more arguments:  
 `key-to-override.mod = pySelf: oldAttrs: oldVal: ...;`
 - allow derivations passed as `src` argument to buildPythonPackage
 - stop inheriting attribute names from nixpkgs, instead use normalized package names
 - rework the public API of mach-nix (largely downwards compatible)
 - add example on how to build aarch64 image containing a mach-nix env
 - tests are now enabled/disabled via global override which is more reliable
 - raise error if python version of any package in packagesExtra doesn't match to one of the environment


### Fixes
 - nixpkgs packages with identical versions swallowed
 - pname/version null in buildPythonPackage
 - update dependency extractor to use "LANG=C.utf8" (increases available packages for python 3.5 and 3.6)
 - wheel provider picked wheels incompatible to python version
 - unwanted python buildInput inheritance when overriding nixpkgs
 - properly parse setup/install_requires if they are strings instead of lists
 
### Package Fixes
 - rpy2: sdist: remove conflicting patch for versions newer than 3.2.6
 - pytorch from nixpkgs was not detected as `torch`
 - pyqt5: fix for providers nixpkgs and wheel
 - httpx: remove patches


# 2.4.1 (21 Sep 2020)
bugfixes

### Fixes
 - `extra_pkgs` was broken: Packages didn't end up in final environment
 - null value error when inheriting passthru for disabled packages
 - Wrong provider detected for `sdist` packages in fixes.nix
 - overrides from fixes.nix didn't apply for `buildPythonPackage`
  
### Package Fixes
 - pip: allow from `sdist` provider
 - pip: remove `reproducible.patch` for versions < 20.0


# 2.4.0 (20 Sep 2020)
Global conditional overrides, simple overrides for buildPythonPackage, improved metadata extraction, fix wheel selection

### Features
 - **Global conditional overrides**: Similar to the overrides from poetry2nix, this allows users to upstream their 'fixes' for python packages. Though, a special format is used here which is optimized for human readability and allows to define a condition for each fix. Therefore fixes are applied on a granular basis depending on the metadata of each package like its `version`, `python version`, or `provider`. This format is designed in a way, so it could easily be reused by projects other than mach-nix. Please contribute your fixes to [./mach_nix/fixes.nix](https://github.com/DavHau/mach-nix/blob/master/mach_nix/fixes.nix)
 - Simplified overrides are now also available for buildPythonPackage (underscore argument)
 - Inherit passthru from nixpkgs: Reduces risk of missing attributes like `numpy.blas`.
 - Allow passing a string to the `python` argument of mkPython: Values like, for example, `"python38"` are now accepted in which case `pkgs.python38` will be used. The intention is to reduce the risk of accidentally mixing multiple nixpkgs versions.
 - Improved error handling while extracting metadata from python sources in buildPythonPackage.
 
### Fixes
 - Selecting `extras` when using `buildPythonPackage` didn't have any effect
 - The `passthru` argument for `buildPythonPackage` was ignored
 - The `propagatedBuildInputs` argument for `buildPythonPackage` was ignored
 - Wheels with multiple python versions in their filename like `PyQt5-...-cp35.cp36.cp37.cp38-...whl` were not selected correctly.
 
### Package Fixes:
  - tensorflow: collision related to tensorboard
  - orange3: broken .so file caused by fixupPhase (probably due to shrinking)
  - ldap0: add misssing build inputs.

# 2.3.0 (26 Aug 2020)
simplified override system, autodetect requirements, improved success rate

### Features
 - Simplified generic override system via `_` (underscore) argument for `mkPython`.  
   Example: `_.{package}.buildInputs.add = [...]`
 - `buildPythonPackage` now automatically detects requirements. Therefore the `requrements` argument becomes optional.
 - `buildPythonPackage` now automatically detects package `name` and `version`. Therefore those attributes become optional.
 - `buildPythonPackage` can now be called while only passing a tarball url or a path
 - `mkPython` allows to include python packages from arbitrary sources via new argument `extra_pkgs`
 - `mkPython` can now be called while only passing a list of tarball urls or paths

### Fixes
 - More bugs introduced by packages with dot in name
 - Definitions from `overrides_pre` were sometimes disregarded due to wrong use of `with`-statements inside a recursive attrset.
 - Fix installation of the mach-nix tool via pip. (requirements were missing)
 - packages which use a non-normalized version triggered an evaluation error since mach-nix tried to reference their source via normalized version.
 - wheels removed from pypi were not removed from the dependency graph which could result in environments failing to build
 

# 2.2.2 (17 Aug 2020)

### Fixes
 - Packages with dot in name led to invalid nix expression
 - Problem generating error message for resolution impossible errors
 - `buildPythonPackage` of mach-nix failed if arguments like `pkgs` were passed.
 - When overriding packages, mach-nix now falls back to using `overrideAttrs` if `overridePythonAttrs` is not available.
 
### Package Fixes:
 - pip: installation failed. Fixed by forcing `nixpkgs` provider
 - gdal: building from sdist doesn't work. Fixed by forcing `nixpkgs` provider

### Development
 - Merged project `pypi-crawlers` into mach-nix (was separated project before)


# 2.2.1 (11 Aug 2020)
Handle circular dependencies, fix python 3.8 wheels, improve error message

### Features
 - Print more detailed info when the resolver raises a ResolutionImpossible error.
 - Warn on circular dependencies and fix them automatically.

### Fixes
 - Fix crash on circular dependencies.
 - Python 3.8 wheels have abi tag cp38, not cp38m. This was not considered before which prevented finding suitable manylinux wheels for python 3.8
 
### Development
 - Added integration tests under [./tests/](/tests/)


# 2.2.0 (09 Aug 2020)
Improved success rate, MacOS support, bugfixes, optimizations

### Features
 - Improved selection of wheel releases. MacOS is now supported and architectures besides x86_64 should be handled correctly.
 - Whenever mach-nix resolves dependencies, a visualization of the resulting dependency tree is printed on the terminal. 
 - The dependency DB is now accessed through a caching layer which reduces the resolver's CPU time significantly for larger environments.
 - The python platform context is now generated from the nix build environment variable `system`. This should decrease the chance of impurities during dependency resolution.
 
### Fixes
 - The requires_python attribute of wheels was not respected. This lead to failing builds especially for older python versions. Now `requires_python` is part of the dependency graph and affects resolution.
 - Detecting the correct package name for python packages in nixpkgs often failed since the attribute names don't follow a fixed schema. This lead to a handful of different errors in different situations. Now the package names are extracted from the pypi `url` inside the `src` attribute which is much more reliable. For packages which are not fetched from pypi, the `pname` attribute is used as fallback.
 - Fixed bug which lead to the error `attribute 'sdist' missing` if a package from the nixpkgs provider was used which doesn't publish it's source on pypi. (For example `tensorflow`)
 
### Other Changes
 - Mach-nix now uses a revision of the nixpkgs-unstable branch instead of nixos-20.03 as base fo the tool and the nixpkgs provider.
 - Updated revision of the dependency DB


# 2.1.1 (30 Jul 2020)
Fix broken wheel packages
### Fixes:
 - Some wheel packages could brake through patchelf if they already contained stripped binaries. Packages like numpy wouldn't work because of this. This is now fixed by passing `dontStrip` to the `autoPatchelf` routine.


# 2.1.0 (04 Jul 2020)
Bug fixes + new feature **buildPythonPackage** / **buildPythonApplication**
### Fixes:
 - fix `value is null while a set was expected` error when python package is used which is set to null in nixpkgs.

### Features:
 - **buildPythonPackage** / **buildPythonApplication**: Interface to build python packages from their source code + requirements.txt


# 2.0.1 (29 Jun 2020)
Improves build-time closure, build success rate and fixes disable_checks option.
### Fixes:
 - fix: `disable_checks` did not work for packages built via the `sdist` provider if the required version matches exactly the version used in nixpkgs.
 - fix: some dependencies with markers were ignored completely
 - fix: providers `nixpkgs` and `sdist` inherited many unneeded build inputs from nixpkgs leading to bloated build-time closures, increased failure rate and uneffective `disable_checks` option. After this fix, only non-python build-inputs are inherited from nixpkgs.
 - mach-nix now sets `pname` + `version` for python packages instead of `name`


# 2.0.0
### Features:
 - **Python Wheels**: Wheels are supported for linux including manylinux1, manylinux2010, manylinux2014
 - **Nixpkgs python packages**: Nixpkgs is now treated as a separate provider. That means packages can be taken directly from there, independent on their availability from pypi.
 - **Configurable Providers**: The user can now freely decide where packages should be taken from either via a default or on a per package basis. Currently available provider are `nixpkgs`, `sdist`, `wheel`.
 - **Core architecture - Python Overrides**: The core of mach nix now produces python overrides instead of nixpkgs overlays which makes it much more composible and allows for a less strange API.
 - **Overlay support**: `mkPython` and lower level interfaces now accept new parameter `pkgs` and `python` which indirectly enables you to use any nixpkgs overlays (But don't use this for modifying python packages. Better do this with **Python Overrides**)
 - **Python Overrides support**: `mkPython` now accepts new parameter `overrides_pre` and `overrides_post` each allowing to inject a list of python overrides to apply before and after the mach-nix internal overrides. This allows you to fixup packages or add your own modifications to them.
 - **Extras support**: All providers now fully support python [extras](https://www.python.org/dev/peps/pep-0508/#extras). That means requirements like for example '`requests[security]`' will be correctly resolved.

### Nix Interface changes:
 - Removed:  
    - **mkPythonExpr**: removed in favor of `machNixFile` and `machNix`
 - Added:  
    - **machNixFile** which generates a nex expresison
    - **machNix** which evaluates the generated nix expression to get `overrides` and `select_pkgs`
 - Changed:  
    - **mkPython**:
        - Removed arguments:
            - `python_attr` in favor if `python`
            - `prefer_nixpkgs` in favor of `providers`
            - `nixpkgs_commit` in favor of `pkgs`
            - `nixpkgs_tarball_sha256` in favor of `pkgs`
        - Added arguments:
            - `overrides_pre`: list of python overrides to apply before the machnix overrides
            - `overrides_post`: list of python overrides to apply after the machnix overrides
            - `pkgs`: pass custom nixpkgs. Only used for manylinux wheel dependencies.
            - `providers`: define provider preferences
            - `_provider_defaults`: builtin provider defaults. Disable them by passing {}


# 1.0.0
Initial Release
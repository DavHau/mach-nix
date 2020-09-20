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
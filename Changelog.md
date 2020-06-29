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
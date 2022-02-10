with builtins;
let
  mach-nix = import ../. {};
  lib = mach-nix.nixpkgs.lib;
  conda = (getEnv "CONDA_TESTS") != "";
  makeTests = {file}:
      import file ({
        inherit mach-nix;
      } // (if conda then (rec {
        baseArgsMkPython = { _providerDefaults = (fromTOML (readFile ../mach_nix/provider_defaults.toml) // {
          _default = "conda,wheel,sdist,nixpkgs";
        }); };
        baseArgsBuildPythonPackage = baseArgsMkPython;
      }) else rec {
        baseArgsMkPython = { _providerDefaults = fromTOML (readFile ../mach_nix/provider_defaults.toml); };
        baseArgsBuildPythonPackage = baseArgsMkPython;
      }));
in makeTests

with builtins;
let
  mach-nix = import ../. {};
  conda = (getEnv "CONDA_TESTS") != "";
  makeTest = file:
      import file ({
        inherit mach-nix;
      } // (if conda then (rec {
        baseArgsMkPython = { _provierDefaults = fromTOML (readFile ./mach_nix/provider_defaults.toml); };
        baseArgsBuildPythonPackage = baseArgsMkPython;
      }) else {}));
in
flatten (map (file: makeTests) [
  ./test_alias_dateutil.nix
  ./test_circular_deps.nix
  ./test_dot_in_name.nix
  ./test_extra_pkgs.nix
  ./test_extras.nix
  ./test_flakes.nix
  ./test_jupyterlab_nixpkgs.nix
  ./test_lazy_usage.nix
  ./test_non_python_extra_pkgs.nix
  ./test_overrides_selectPkgs.nix
  ./test_passthru_select_pypi_pname.nix
  ./test_py38_cp38_wheel.nix
  ./test_pymc3.nix
  ./test_r_pkgs.nix
  ./test_underscore_override.nix
  ./test_underscore_override_extra.nix
])
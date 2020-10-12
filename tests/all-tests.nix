let
  mach-nix = import ../. {};
in
map (file: import file { inherit mach-nix; }) [
  ./test_circular_deps.nix
  ./test_dot_in_name.nix
  ./test_extra_pkgs.nix
  ./test_extras.nix
  ./test_jupyterlab_nixpkgs.nix
  ./test_r_pkgs.nix
  ./test_lazy_usage.nix
  ./test_passthru_select_pypi_pname.nix
  ./test_py38_cp38_wheel.nix
  ./test_pymc3.nix
  ./test_underscore_override.nix
  ./test_underscore_override_extra.nix
]
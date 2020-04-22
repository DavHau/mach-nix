let
  pkgs =  import (import ../mach_nix/nix/nixpkgs-src.nix).stable {};
  commit = builtins.readFile ../mach_nix/nix/PYPI_DEPS_DB_COMMIT;
  sha256 = builtins.readFile ../mach_nix/nix/PYPI_DEPS_DB_TARBALL_SHA256;
  src = builtins.fetchTarball {
    name = "pypi-deps-db-src";
    url = "https://github.com/DavHau/pypi-deps-db/tarball/${commit}";
    inherit sha256;
  };
in
pkgs.buildEnv {
  name = "pypi-deps-db-src";
  paths = [ src ];
}

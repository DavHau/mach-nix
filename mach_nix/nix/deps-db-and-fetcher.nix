{
  pkgs ? import (import ./nixpkgs-src.nix) {},
  pypi_deps_db_commit ? ((import ./flake-inputs.nix) "pypi-deps-db").rev,
  pypi_deps_db_sha256 ? ((import ./flake-inputs.nix) "pypi-deps-db").sha256,
  deps_db_src ? fetchTarball {
    name = "pypi-deps-db-src";
    url = "https://github.com/DavHau/pypi-deps-db/tarball/${pypi_deps_db_commit}";
    sha256 = "${pypi_deps_db_sha256}";
  }
}:
with pkgs.lib;
let
  pypi_fetcher_commit = removeSuffix "\n" (readFile "${deps_db_src}/PYPI_FETCHER_COMMIT");
  pypi_fetcher_sha256 = removeSuffix "\n" (readFile "${deps_db_src}/PYPI_FETCHER_SHA256");
  pypi_fetcher_src = fetchTarball {
    name = "nix-pypi-fetcher-src";
    url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/${pypi_fetcher_commit}";
    sha256 = "${pypi_fetcher_sha256}";
  };
  pypi_fetcher = import pypi_fetcher_src {
    inherit pkgs;
  };
in
{
  pypi_deps_db_src = deps_db_src;
  inherit
    pypi_deps_db_src
    pypi_fetcher_src

    pypi_fetcher_commit
    pypi_fetcher_sha256

    pypi_fetcher;
}

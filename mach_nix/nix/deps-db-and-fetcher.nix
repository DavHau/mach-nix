{
  pkgs,
  pypi_deps_db_commit ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).rev,
  pypi_deps_db_sha256 ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).sha256,
}:
with pkgs.lib;
let
  pypi_deps_db_src = fetchTarball {
    name = "pypi-deps-db-src";
    url = "https://github.com/DavHau/pypi-deps-db/tarball/${pypi_deps_db_commit}";
    sha256 = "${pypi_deps_db_sha256}";
  };
  pypi_fetcher_commit = removeSuffix "\n" (readFile "${pypi_deps_db_src}/PYPI_FETCHER_COMMIT");
  pypi_fetcher_sha256 = removeSuffix "\n" (readFile "${pypi_deps_db_src}/PYPI_FETCHER_SHA256");
  pypi_fetcher_src = fetchTarball {
    name = "nix-pypi-fetcher-src";
    url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/${pypi_fetcher_commit}";
    sha256 = "${pypi_fetcher_sha256}";
  };
  pypi_fetcher = import pypi_fetcher_src {
    inherit pkgs;
  };
in
{ inherit
  pypi_deps_db_src
  pypi_fetcher_src

  pypi_fetcher_commit
  pypi_fetcher_sha256

  pypi_fetcher; }

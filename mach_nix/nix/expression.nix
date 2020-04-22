{
  requirements,
  nixpkgs_src ? (import ./nixpkgs-src.nix).stable,  # to take python packages from
  python_attr ? "python3",  # python attr name inside given nixpkgs. Used as base for resulting python environment
  prefer_nixpkgs ? true, # Prefer python package versions from nixpkgs instead of newer ones. Decreases build time.
  disable_checks ? true, # Disable tests wherever possible to decrease build time.
  nixpkgs_commit ? builtins.readFile ./NIXPKGS_COMMIT,
  nixpkgs_tarball_sha256 ? builtins.readFile ./NIXPKGS_TARBALL_SHA256,
  pypi_deps_db_commit ? builtins.readFile ./PYPI_DEPS_DB_COMMIT,
  # Hash obtained using `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>.tar.gz`
  pypi_deps_db_sha256 ? builtins.readFile ./PYPI_DEPS_DB_TARBALL_SHA256
}:
let
  nixpkgs_src = builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_commit}";
    sha256 = "${nixpkgs_tarball_sha256}";
  };
  pkgs = import nixpkgs_src { config = {}; };
  python = pkgs."${python_attr}";
  nixpkgs_json = import ./nixpkgs-json.nix { inherit pkgs python; };
  builder_pkgs = import (import ./nixpkgs-src.nix).stable { config = {}; };
  app = import ../../default.nix;
  builder_python = pkgs.python37.withPackages(ps:
    (pkgs.lib.attrValues (pkgs.callPackage ./python-deps.nix {}) ++ [ app ])
  );
  pypi_deps_db_src = builtins.fetchTarball {
    name = "pypi-deps-db-src";
    url = "https://github.com/DavHau/pypi-deps-db/tarball/${pypi_deps_db_commit}";
    sha256 = "${pypi_deps_db_sha256}";
  };
  pypi_fetcher_commit = builtins.readFile "${pypi_deps_db_src}/PYPI_FETCHER_COMMIT";
  pypi_fetcher_tarball_sha256 = builtins.readFile "${pypi_deps_db_src}/PYPI_FETCHER_TARBALL_SHA256";
  pypi_fetcher_src = builtins.fetchTarball {
    name = "nix-pypi-fetcher-src";
    url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/${pypi_fetcher_commit}";
    sha256 = "${pypi_fetcher_tarball_sha256}";
  };
  expression = pkgs.runCommand "python-expression"
    { buildInputs = [ builder_python pypi_deps_db_src];
      inherit disable_checks nixpkgs_commit nixpkgs_tarball_sha256 nixpkgs_json
              prefer_nixpkgs requirements pypi_fetcher_commit pypi_fetcher_tarball_sha256;
      py_ver_str = python.version;
      pypi_deps_db_data_dir = "${pypi_deps_db_src}/data";
    }
    ''
      mkdir -p $out/share
      export out_file=$out/share/expr.nix
      export PYTHONPATH=${app}/lib/python3.7/site-packages/
      ${builder_python}/bin/python ${builder_python}/lib/python3.7/site-packages/mach_nix/generate.py
    '';
in
expression
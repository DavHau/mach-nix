{
  requirements,  # content from a requirements.txt file
  python_attr ? "python3",  # python attr name inside given nixpkgs. Used as base for resulting python environment
  prefer_nixpkgs ? true,  # Prefer python package versions from nixpkgs instead of newer ones. Decreases build time.
  disable_checks ? true,  # Disable tests wherever possible to decrease build time.
  nixpkgs_commit ? builtins.readFile ./NIXPKGS_COMMIT,  # nixpkgs version to use python packages from
  nixpkgs_tarball_sha256 ? builtins.readFile ./NIXPKGS_TARBALL_SHA256,  # nixpkgs version to use python packages from
  pypi_deps_db_commit ? builtins.readFile ./PYPI_DEPS_DB_COMMIT,  # python dependency DB version to use
  # Hash obtained using `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`
  pypi_deps_db_sha256 ? builtins.readFile ./PYPI_DEPS_DB_TARBALL_SHA256  # python dependency DB version to use
}:
let
  nixpkgs_src = (import ./nixpkgs-src.nix).stable;
  pkgs = import nixpkgs_src { config = {}; overlays = []; };
  target_nixpkgs_src = builtins.fetchTarball {
    name = "nixpkgs";
    url = "https://github.com/nixos/nixpkgs/tarball/${nixpkgs_commit}";
    sha256 = "${nixpkgs_tarball_sha256}";
  };
  target_pkgs = import target_nixpkgs_src { config = {}; overlays = []; };
  target_python = target_pkgs."${python_attr}";
  nixpkgs_json = import ./nixpkgs-json.nix { pkgs = target_pkgs; python = target_python; };
  builder_python = pkgs.python37.withPackages(ps:
    (pkgs.lib.attrValues (import ./python-deps.nix {python = pkgs.python37; fetchurl = pkgs.fetchurl; }))
  );
  src = ./../../.;
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
    { buildInputs = [ src builder_python pypi_deps_db_src];
      inherit disable_checks nixpkgs_commit nixpkgs_tarball_sha256 nixpkgs_json
              prefer_nixpkgs requirements pypi_fetcher_commit pypi_fetcher_tarball_sha256;
      py_ver_str = target_python.version;
      pypi_deps_db_data_dir = "${pypi_deps_db_src}/data";
    }
    ''
      mkdir -p $out/share
      export out_file=$out/share/expr.nix
      export PYTHONPATH=${src}
      ${builder_python}/bin/python ${src}/mach_nix/generate.py
    '';
in
expression

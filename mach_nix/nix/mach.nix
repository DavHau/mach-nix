{
  requirements,  # content from a requirements.txt file
  python,  # python from nixpkgs as base for overlay
  disable_checks ? true,  # disable tests wherever possible
  prefer_new ? false,  # prefer newest python package versions disregarding the provider priority
  providers ? {},  # re-order to change provider priority or remove providers
  pypi_deps_db_commit ? builtins.readFile ./PYPI_DEPS_DB_COMMIT,  # python dependency DB version
  # Hash obtained using `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`
  pypi_deps_db_sha256 ? builtins.readFile ./PYPI_DEPS_DB_SHA256,
  _provider_defaults ? with builtins; fromTOML (readFile ../provider_defaults.toml)
}:
let
  nixpkgs_src = (import ./nixpkgs-src.nix).stable;
  pkgs = import nixpkgs_src { config = {}; overlays = []; };
  nixpkgs_json = import ./nixpkgs-json.nix { inherit pkgs python; };
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
  pypi_fetcher_sha256 = builtins.readFile "${pypi_deps_db_src}/PYPI_FETCHER_SHA256";
  pypi_fetcher_src = builtins.fetchTarball {
    name = "nix-pypi-fetcher-src";
    url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/${pypi_fetcher_commit}";
    sha256 = "${pypi_fetcher_sha256}";
  };
  providers_json = builtins.toJSON ( _provider_defaults // providers);
  mach_nix_file = pkgs.runCommand "mach_nix_file"
    { buildInputs = [ src builder_python pypi_deps_db_src];
      inherit disable_checks nixpkgs_json prefer_new
              requirements pypi_deps_db_src pypi_fetcher_commit pypi_fetcher_sha256;
      providers = providers_json;
      py_ver_str = python.version;
    }
    ''
      mkdir -p $out/share
      export out_file=$out/share/mach_nix_file.nix
      export PYTHONPATH=${src}
      ${builder_python}/bin/python ${src}/mach_nix/generate.py
    '';
in
# single file derivation containing $out/share/mach_nix_file.nix
mach_nix_file

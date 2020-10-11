{
  requirements,  # content from a requirements.txt file
  python,  # python from nixpkgs as base for overlay
  pkgs,
  disable_checks ? true,  # disable tests wherever possible
  overrides ? [],
  providers ? {},  # re-order to change provider priority or remove providers
  pypi_deps_db_commit ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).rev,  # python dependency DB version
  # Hash obtained using `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`
  pypi_deps_db_sha256 ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).sha256,
  _provider_defaults ? with builtins; fromTOML (readFile ../provider_defaults.toml)
}:
let
  nixpkgs_json = import ./nixpkgs-json.nix {
    inherit overrides pkgs python;
    mergeOverrides = with pkgs.lib; foldl composeExtensions (self: super: { });
  };
  builder_python = pkgs.python37.withPackages(ps:
    (pkgs.lib.attrValues (import ./python-deps.nix {python = pkgs.python37; fetchurl = pkgs.fetchurl; }))
  );
  src = ./../../.;
  db_and_fetcher = import ./deps-db-and-fetcher.nix { inherit pkgs; };
  providers_json = builtins.toJSON ( _provider_defaults // providers);
  mach_nix_file = pkgs.runCommand "mach_nix_file"
    { buildInputs = [ src builder_python db_and_fetcher.pypi_deps_db_src];
      inherit disable_checks nixpkgs_json requirements;
      inherit (db_and_fetcher) pypi_deps_db_src pypi_fetcher_commit pypi_fetcher_sha256;
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

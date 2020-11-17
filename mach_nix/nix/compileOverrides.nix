{
  requirements,  # content from a requirements.txt file
  python,  # python from nixpkgs as base for overlay
  pkgs,
  condaChannelsExtra ? {},
  tests ? false,  # disable tests wherever possible
  overrides ? [],
  providers ? {},  # re-order to change provider priority or remove providers
  pypiDataRev ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).rev,  # python dependency DB version
  # Hash obtained using `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`
  pypiDataSha256 ? (builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json)).sha256,
  _providerDefaults ? with builtins; fromTOML (readFile ../provider_defaults.toml)
}:
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  _providers = l.parseProviders (_providerDefaults // providers);

  nixpkgs_json = import ./nixpkgs-json.nix {
    inherit overrides pkgs python;
  };

  builder_python = pkgs.python37.withPackages(ps:
    (pkgs.lib.attrValues (import ./python-deps.nix {python = pkgs.python37; fetchurl = pkgs.fetchurl; }))
  );

  src = ./../../.;

  db_and_fetcher = import ./deps-db-and-fetcher.nix {
    inherit pkgs;
    pypi_deps_db_commit = pypiDataRev;
    pypi_deps_db_sha256 = pypiDataSha256;
  };

  providers_json_file = pkgs.writeText "providers" (builtins.toJSON _providers);
  mach_nix_file = pkgs.runCommand "mach_nix_file"
    { buildInputs = [ src builder_python db_and_fetcher.pypi_deps_db_src];
      inherit nixpkgs_json requirements;
      inherit (db_and_fetcher) pypi_deps_db_src pypi_fetcher_commit pypi_fetcher_sha256;
      conda_channels_json =  (import ./conda-channels.nix {
        inherit condaChannelsExtra pkgs;
        providers = _providers;
      }).condaChannelsJson;
      disable_checks = ! tests;
      providers = providers_json_file;
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

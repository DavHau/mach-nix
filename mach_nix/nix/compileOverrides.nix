with builtins;
{
  requirements,  # content from a requirements.txt file
  python,  # python from nixpkgs as base for overlay
  pkgs,
  condaChannelsExtra ? {},
  tests ? false,  # disable tests wherever possible
  overrides ? [],
  providers ? {},  # re-order to change provider priority or remove providers
  pypiData,
  condaDataRev ? (builtins.fromJSON (builtins.readFile ./CONDA_CHANNELS.json)).rev,
  condaDataSha256 ? (builtins.fromJSON (builtins.readFile ./CONDA_CHANNELS.json)).indexSha256,
  cudaVersion ? pkgs.cudatoolkit.version,  # max allowed cuda version for conda packages
  _providerDefaults ? (import ./lib.nix { inherit (pkgs) lib; inherit pkgs; }).makeProviderDefaults requirements
}:

with pkgs.lib;
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  processedReqs = l.preProcessRequirements requirements;

  _requirements = processedReqs.requirements;

  __providerDefaults = l.parseProviders _providerDefaults;

  _providers =
    let
      extraChannelProviders =(map (n: "conda/" + n) (attrNames condaChannelsExtra));
      extraProviders =
        extraChannelProviders
        ++ filter (p: ! extraChannelProviders ? p) processedReqs.providers;
      defaults = recursiveUpdate __providerDefaults {
        _default =
            __providerDefaults._default
            ++ (filter (p: ! elem p __providerDefaults._default) extraProviders);
      };
    in
      (l.parseProviders (defaults // providers));

  nixpkgs_json = import ./nixpkgs-json.nix {
    inherit overrides pkgs python;
  };
  builder_python = pkgs.pkgsBuildHost.python39.withPackages(ps:
    (pkgs.lib.attrValues (import ./python-deps.nix {python = pkgs.python39; fetchurl = pkgs.fetchurl; }))
  );

  src = ./../../.;

  db_and_fetcher = import ./deps-db-and-fetcher.nix {
    inherit pkgs;
    deps_db_src = pypiData;
  };

  providers_json_file = pkgs.writeText "providers" (builtins.toJSON _providers);
  mach_nix_file = pkgs.runCommand "mach_nix_file"
    { buildInputs = [ src builder_python db_and_fetcher.pypi_deps_db_src];
      inherit nixpkgs_json;
      inherit (db_and_fetcher) pypi_deps_db_src pypi_fetcher_commit pypi_fetcher_sha256;
      conda_channels_json =  (import ./conda-channels.nix {
        inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs;
        providers = _providers;
      }).condaChannelsJson;
      disable_checks = ! tests;
      providers = providers_json_file;
      py_ver_str = python.version;
      requirements = _requirements;
    }
    ''
      mkdir -p $out/share
      export out_file=$out/share/mach_nix_file.nix
      export PYTHONPATH=${src}
      export MACHNIX_CUDA_VERSION=${cudaVersion}
      ${builder_python}/bin/python ${src}/mach_nix/generate.py
    '';
in
# single file derivation containing $out/share/mach_nix_file.nix
traceValFn (drv: "${drv.outPath} ${python}") mach_nix_file

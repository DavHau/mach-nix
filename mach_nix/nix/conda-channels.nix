{
  condaChannelsExtra ? {},
  pkgs ? import (import ./nixpkgs-src.nix) {},
  providers ? builtins.fromJSON (builtins.readFile (builtins.getEnv "providers")),
  system ? "x86_64-linux",

  # conda-channels index
  repoName ? "conda-channels",
  repoOwner ? "DavHau",
  rev ? "e742cc6152473ddffb33e91181ff5d1b23222fc8",
  sha256 ? "1dqxni9yjk1g327blmz3n9fmnp7vs9syr3hf7xzhnramkng1fb30",
}:
with builtins;
with pkgs.lib;
let

  systemMap = {
    x86_64-linux = "linux-64";
    x86_64-darwin = "osx-64";
    aarch64-linux = "linux-aarch64";
  };

  allProviders = flatten (attrValues providers);

  usedChannels =
    filter (p: p != null)
      (map (p: if hasPrefix "conda/" p then removePrefix "conda/" p else null) allProviders);

  channelRegistry = fromJSON (readFile (fetchurl {
    name = "conda-channels-index";
    url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${rev}/sha256.json";
    inherit sha256;
  }));

  registryChannels = mapAttrs' (filepath: hash:
    let
      split = splitString "/" filepath;
      chan = elemAt split 1;
      sys = removeSuffix ".json" (tail split);
    in
      nameValuePair
        chan
        (map (sys: (builtins.fetchurl {
          url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${rev}/${chan}/${sys}.json";
          sha256 = channelRegistry."./${chan}/${sys}.json";
        })) [ systemMap."${system}" "noarch" ])
  ) channelRegistry;

  _registryChannels = filterAttrs (chan: json: elem chan usedChannels) registryChannels;

  _condaChannelsExtra = filterAttrs (chan: json: elem chan usedChannels) condaChannelsExtra;

  allCondaChannels = (_registryChannels // _condaChannelsExtra);

  condaChannelsJson = pkgs.writeText "conda-channels.json" (toJSON allCondaChannels);

  missingChannels = filter (c:
    ! elem c ((attrNames registryChannels) ++ (attrNames condaChannelsExtra))
  ) usedChannels;

in
if missingChannels != [] then
  throw "Conda channels [${toString missingChannels}] are unknown. Use 'condaChannelsExtra' to make them available"
else
  trace "using conda channels: ${toString (concatStringsSep ", " (attrNames allCondaChannels))}"
  { inherit condaChannelsJson; }

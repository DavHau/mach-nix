{
  condaChannelsExtra ? {},
  pkgs ? import (import ./nixpkgs-src.nix) {},
  providers ? builtins.fromJSON (builtins.readFile (builtins.getEnv "providers")),
  system ? "x86_64-linux",

  # conda-channels index
  repoName ? "conda-channels",
  repoOwner ? "DavHau",
  condaDataRev ? (builtins.fromJSON (builtins.readFile ./CONDA_CHANNELS.json)).rev,
  condaDataSha256 ? (builtins.fromJSON (builtins.readFile ./CONDA_CHANNELS.json)).indexSha256
}:
with builtins;
with pkgs.lib;
let

  systemMap = {
    x86_64-linux = "linux-64";
    x86_64-darwin = "osx-64";
    aarch64-darwin = "osx-arm64";
    aarch64-linux = "linux-aarch64";
  };

  allProviders = flatten (attrValues providers);

  usedChannels =
    filter (p: p != null)
      (map (p: if hasPrefix "conda/" p then removePrefix "conda/" p else null) allProviders);

  channelRegistry = fromJSON (readFile (fetchurl {
    name = "conda-channels-index";
    url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${condaDataRev}/sha256.json";
    sha256 = condaDataSha256;
  }));

  registryChannels = foldl' (a: b: recursiveUpdate a b) {} (mapAttrsToList (path: sha256:
    let
      split = splitString "/" path;
      chan = elemAt split 1;
      file = last split;
      sys = head (splitString "." file);
      part = elemAt (splitString "." file) 1;
    in {
      "${chan}" = {
        "${sys}" = {
          "${part}" = sha256;
        };
      };
    }
  ) channelRegistry);

  channelFiles = chan: flatten (forEach [ systemMap."${system}" "noarch" ] (sys:
    if registryChannels ? "${chan}"."${sys}" then
      mapAttrsToList (part: sha256: builtins.fetchurl {
        url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${condaDataRev}/channels/${chan}/${sys}.${part}.json";
        sha256 = channelRegistry."channels/${chan}/${sys}.${part}.json";
      }) registryChannels."${chan}"."${sys}"
    else
      []
  ));

  _selectedRegistryChannels =

    genAttrs usedChannels (chan: channelFiles chan);

  _condaChannelsExtra = filterAttrs (chan: json: elem chan usedChannels) condaChannelsExtra;

  allCondaChannels = (_selectedRegistryChannels // _condaChannelsExtra);

  condaChannelsJson = pkgs.writeText "conda-channels.json" (toJSON allCondaChannels);

  missingChannels = filter (c:
    ! elem c ((attrNames registryChannels) ++ (attrNames condaChannelsExtra))
  ) usedChannels;

in
if missingChannels != [] then
  throw "Conda channels [${toString missingChannels}] are unknown. Use 'condaChannelsExtra' to make them available"
else let
  channelNames = (attrNames allCondaChannels); in
  if channelNames != [] then
    trace "using conda channels: ${toString (concatStringsSep ", " (attrNames allCondaChannels))}"
    { inherit condaChannelsJson; }
  else
    { inherit condaChannelsJson; }

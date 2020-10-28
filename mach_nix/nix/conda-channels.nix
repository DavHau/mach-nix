{
  pkgs ? import (import ./nixpkgs-src.nix) {},
  system ? "x86_64-linux",
  channels ? [ "main" "r" "conda-forge" ],
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
  channelIndex = fromJSON (readFile (fetchurl {
    name = "conda-channels-index";
    url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${rev}/sha256.json";
    inherit sha256;
  }));
  condaChannels = listToAttrs (map (chan: nameValuePair chan (
    map ( sys:
      (builtins.fetchurl {
        url = "https://raw.githubusercontent.com/${repoOwner}/${repoName}/${rev}/${chan}/${sys}.json";
        sha256 = channelIndex."./${chan}/${sys}.json";
      })
    ) [ systemMap."${system}" "noarch" ]
  )) channels);
  condaChannelsJson = pkgs.writeText "conda-channels.json" (toJSON condaChannels);
in
{ inherit
    condaChannels
    condaChannelsJson;
}

with builtins;
let
  mach-nix = import ../. {};
  lib = mach-nix.nixpkgs.lib;
  makeTests = import ./make-tests.nix;
  testNames = lib.mapAttrsToList (n: v: lib.removeSuffix ".nix" n) (lib.filterAttrs (n: v: lib.hasPrefix "test_" n && lib.hasSuffix ".nix" n) (builtins.readDir ./.));
in
  lib.flatten (map (name: makeTests { file = ./${name}.nix; }) testNames)

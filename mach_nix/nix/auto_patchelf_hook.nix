{fetchurl, makeSetupHook, writeText}:
let
  autoPatchelfHook = makeSetupHook { name = "auto-patchelf-hook-machnix"; }
    ./from-nixpkgs/auto-patchelf.sh;
in
autoPatchelfHook

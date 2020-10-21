{fetchurl, makeSetupHook, writeText}:
let
  auto_patchelf_script = fetchurl {
    url = "https://raw.githubusercontent.com/NixOS/nixpkgs/c8c09b7dda6061bb11c6f893c0be04db83461765/pkgs/build-support/setup-hooks/auto-patchelf.sh";
    sha256 = "vUVhP2vbuOaWhF/IO5Xl3oMsuEvQ/jAh9zimoZ4oxlc=";
    postFetch = ''
      patch $out ${./auto-patchelf.patch}
    '';
  };
  autoPatchelfHook = makeSetupHook { name = "auto-patchelf-hook-machnix"; }
    auto_patchelf_script;
in
autoPatchelfHook
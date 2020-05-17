{fetchurl, makeSetupHook, writeText}:
let
  patch_file =  writeText "my-file" ''
    --- auto-patchelf.sh
    +++ auto-patchelf.sh
    @@ -141,7 +141,7 @@ autoPatchelfFile() {
         # This makes sure the builder fails if we didn't find a dependency, because
         # the stdenv setup script is run with set -e. The actual error is emitted
         # earlier in the previous loop.
    -    [ $depNotFound -eq 0 ]
    +    [ $depNotFound -eq 0 ] || [ ! -z $autoPatchelfIgnoreNotFound ]

         if [ -n "$rpath" ]; then
             echo "setting RPATH to: $rpath" >&2
  '';
  auto_patchelf_script = fetchurl {
    url = "https://raw.githubusercontent.com/NixOS/nixpkgs/14dd961b8d5a2d2d3b2cf6526d47cbe5c3e97039/pkgs/build-support/setup-hooks/auto-patchelf.sh";
    sha256 = "0y23bnq9ihwzhlp1kjlrq9mv1xnlximhx060pl65g95shq29jsnj";
    postFetch = ''
      patch $out ${patch_file}
    '';
  };
  autoPatchelfHook = makeSetupHook { name = "auto-patchelf-hook-machnix"; }
    auto_patchelf_script;
in
autoPatchelfHook
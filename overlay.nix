# Import this overlay in your project to add the mach-nix namespace
final: prev:
let
  mach-nix-all = import ./. { pkgs = final; };
in
{
  mach-nix = {
    inherit (mach-nix-all)
      mach-nix
      pythonWith
      shellWith
      dockerImageWith
      "with"
      ;

    defaultPackage = mach-nix-all.mach-nix;

    lib = {
      inherit (mach-nix-all)
        mkPython
        mkPythonShell
        mkDockerImage
        mkOverlay
        mkNixpkgs
        mkPythonOverrides

        buildPythonPackage
        buildPythonApplication
        fetchPypiSdist
        fetchPypiWheel
        ;
    };
  };
}

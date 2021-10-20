{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  system ? builtins.currentSystem or "x86_64-linux",
  ...
}:
with builtins;
let
  mkPython = (builtins.getFlake (toString ../.)).lib.${system}.mkPython;
  buildPythonPackage = (builtins.getFlake (toString ../.)).lib.${system}.buildPythonPackage;
in
mkPython [ "https://github.com/psf/requests/tarball/v2.25.0" ]

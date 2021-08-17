{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  mkPython = (builtins.getFlake (toString ../.)).lib.x86_64-linux.mkPython;
  buildPythonPackage = (builtins.getFlake (toString ../.)).lib.x86_64-linux.buildPythonPackage;
in
mkPython [ "https://github.com/psf/requests/tarball/v2.25.0" ]

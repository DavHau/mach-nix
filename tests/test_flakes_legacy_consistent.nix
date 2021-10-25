{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  system ? builtins.currentSystem or "x86_64-linux",
  ...
}:
with builtins;
let
  mkPythonFlakes = (getFlake (toString ../.)).lib.${system}.mkPython;
  pyFlakes = mkPythonFlakes {
    requirements = "requests";
  };
  py = mach-nix.mkPython (baseArgsMkPython // {
    requirements = "requests";
  });
in
if pyFlakes == py then
    py
else
  throw "flakes and legacy output differ"


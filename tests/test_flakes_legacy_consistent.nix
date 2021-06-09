{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  mkPythonFlakes = (getFlake (toString ../.)).lib.x86_64-linux.mkPython;
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


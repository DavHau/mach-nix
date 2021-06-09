# packages with aliases were causing infinite recursions
{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython (baseArgsMkPython // {
  requirements = ''
    python-dateutil
  '';
  providers.python-dateutil = "sdist";
  providers.setuptools-scm = "wheel,sdist,nixpkgs";
})

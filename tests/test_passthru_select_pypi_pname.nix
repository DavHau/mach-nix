# This depends on python-dateutil which triggered an infinite recursion by get_passthru
{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython (baseArgsMkPython // {
  providers._default = "wheel,sdist,nixpkgs";
  requirements = ''
    bokeh
  '';
})

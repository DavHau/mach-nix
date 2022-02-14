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
    pymc3 == 3.11.4
  '';
})

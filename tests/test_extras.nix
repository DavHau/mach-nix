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
    dask[complete]==2.22.0
  '';
})

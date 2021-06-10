{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython (baseArgsMkPython // {
  requirements = ''
    jupyterlab
  '';
  providers.jupyterlab = "nixpkgs";
})

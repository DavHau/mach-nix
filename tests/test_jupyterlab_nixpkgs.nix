{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    jupyterlab
  '';
  providers.jupyterlab = "nixpkgs";
}

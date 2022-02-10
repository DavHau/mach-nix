{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  python = "python38";
  requirements = ''
    numba==0.50.1
  '';
  providers = { numba = "wheel"; };
}

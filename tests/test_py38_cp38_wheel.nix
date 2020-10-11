{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    numba==0.50.1
  '';
  providers = { numba = "wheel"; };
  python = "python38";
}

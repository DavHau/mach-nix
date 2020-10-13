{
  mach-nix ? import ../. {
    python = "python38";
  },
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    numba==0.50.1
  '';
  providers = { numba = "wheel"; };
}

{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    pymc3 == 3.9.3
  '';
}

{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    pymc3 == 3.9.3
  '';
}

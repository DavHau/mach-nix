let
  mach-nix = import ../.;
in mach-nix.mkPython {
  requirements = ''
    pymc3 == 3.9.3
  '';
}

{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    pdfminer.six == 20200726
  '';
}

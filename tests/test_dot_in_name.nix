let
  mach-nix = import ../.;
in mach-nix.mkPython {
  requirements = ''
    pdfminer.six == 20200726
  '';
}

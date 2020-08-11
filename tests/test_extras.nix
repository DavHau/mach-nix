let
  mach-nix = import ../.;
in mach-nix.mkPython {
  requirements = ''
    dask[complete]==2.22.0
    looool
  '';
}

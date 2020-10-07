{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    dask[complete]==2.22.0
  '';
}

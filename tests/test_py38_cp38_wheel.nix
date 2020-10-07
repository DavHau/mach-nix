{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    numba==0.50.1
  '';
  providers = { numba = "wheel"; };
  python = mach-nix.nixpkgs.python38;
}

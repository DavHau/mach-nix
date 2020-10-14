{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    requests
  '';
  packagesExtra = [
    mach-nix.nixpkgs.hello
  ];
}

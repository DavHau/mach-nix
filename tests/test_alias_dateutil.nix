# packages with aliases were causing infinite recursions
{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython {
  requirements = ''
    python-dateutil
  '';
  providers.python-dateutil = "sdist";
}

# This depends on python-dateutil which triggered an infinite recursion by get_passthru
{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    bokeh
  '';
}

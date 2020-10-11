{ mach-nix, ... }:
mach-nix.mkPython {
  requirements = ''
    aiohttp
  '';
  extra_pkgs = [
    "https://github.com/psf/requests/tarball/v2.24.0"
    (mach-nix.buildPythonPackage {
      src = "https://github.com/django/django/tarball/3.1";
      add_requirements = "pytest";
    })
  ];
}

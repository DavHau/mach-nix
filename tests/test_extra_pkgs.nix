let
  mach-nix = import ../.;
in mach-nix.mkPython {
  requirements = ''
    aiohttp
  '';
  extra_pkgs = [
    "https://github.com/psf/requests/tarball/master"
    (mach-nix.buildPythonPackage {
      src = "https://github.com/django/django/tarball/master";
      add_requirements = "pytest";
    })
  ];
}

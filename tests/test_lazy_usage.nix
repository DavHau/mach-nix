{ mach-nix, ... }:
mach-nix.mkPython [
  "https://github.com/psf/requests/tarball/master"
  (mach-nix.buildPythonPackage {
    src = "https://github.com/django/django/tarball/master";
    add_requirements = "pytest";
  })
]

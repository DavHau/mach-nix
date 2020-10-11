{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython [
  "https://github.com/psf/requests/tarball/v2.24.0"
  (mach-nix.buildPythonPackage {
    src = "https://github.com/django/django/tarball/3.1";
    add_requirements = "pytest";
  })
]

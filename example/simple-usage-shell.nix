let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "1.0.0";
  });
in mach-nix.mkPythonShell {
  requirements = builtins.readFile ./requirements.txt;
}

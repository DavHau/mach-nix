let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.0.0";
  });
in mach-nix.mkPythonExpr {
  requirements = builtins.readFile ./requirements.txt;
}

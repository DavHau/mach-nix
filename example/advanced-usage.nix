let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.0.0";
  });
in mach-nix.mkPython {
  requirements = builtins.readFile ./requirements.txt;
  python_attr = "python36";
  prefer_nixpkgs = false;
  disable_checks = true;
  nixpkgs_commit = "60c4ddb97fd5a730b93d759754c495e1fe8a3544";
  nixpkgs_tarball_sha256 = "1a1pvfz130c4cma5a21wjl7yrivc7ls1ksqqmac23srk64ipzakf";
  pypi_deps_db_commit = "ee346b782cd217a4d1483a4749429065a520610b";
  pypi_deps_db_sha256 = "08k7ybvar5d820ygsg87ks14l086x7y0ciamizdj0shw2xkn7cly";
}

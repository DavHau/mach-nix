{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.pypi-deps-db = {
    url = "github:DavHau/pypi-deps-db";
    flake = false;
  };

  outputs = { self, nixpkgs, flake-utils, ... }@inp:
    with nixpkgs.lib;
    let
      dataLastModified = toInt (readFile "${inp.pypi-deps-db}/UNIX_TIMESTAMP");
      dataOutdated =
        if inp.nixpkgs.sourceInfo ? lastModified
            && dataLastModified < inp.nixpkgs.sourceInfo.lastModified then
          true
        else
          false;
      usageGen = "usage: nix (build|develop) mach-nix#gen.(python|shell|docker).package1.package2...";
    in
      (flake-utils.lib.eachDefaultSystem (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          mach-nix-default = import ./default.nix {
            inherit pkgs dataOutdated;
            pypiData = inp.pypi-deps-db;
          };
        in rec
        {
          devShell = import ./shell.nix {
            inherit pkgs;
          };
          packages = rec {
            inherit (mach-nix-default) mach-nix;
            sdist = pkgs.runCommand "mach-nix-sdist"
              { buildInputs = mach-nix-default.pythonDeps; }
              ''
                mkdir src
                cp -r ${./.}/* src
                cd src
                python setup.py sdist -d $out
              '';
            # fake package which contains functions inside passthru
            gen = pkgs.stdenv.mkDerivation {
              name = usageGen;
              src = throw usageGen;
              passthru = {
                python = mach-nix-default.pythonWith;
                shell = mach-nix-defaul.shellWitht;
                docker = mach-nix-default.dockerImageWith;
                inherit (mach-nix-default)
                  pythonWith
                  shellWith
                  dockerImageWith;
              };
            };
          };

          defaultPackage = packages.mach-nix;

          apps.mach-nix = flake-utils.lib.mkApp { drv = packages.mach-nix.mach-nix; };
          defaultApp = { type = "app"; program = "${defaultPackage}/bin/mach-nix"; };

          lib = {
            inherit (mach-nix-default)
              mkPython
              mkPythonShell
              mkDockerImage
              mkOverlay
              mkNixpkgs
              mkPythonOverrides

              buildPythonPackage
              buildPythonApplication
              fetchPypiSdist
              fetchPypiWheel
              ;
          };
        }
      ))

      // # deprecated usage
      {
        pythonWith = {} // throw "\n'pythonWith' is deprecated.\n${usageGen}";
        "with" = {} // throw "\n'with' is deprecated.\n${usageGen}";
        shellWith = {} // throw "\n'shellWith' is deprecated.\n${usageGen}";
        dockerImageWith = {} // throw "\n'dockerImageWith' is deprecated.\n${usageGen}";
      };
}

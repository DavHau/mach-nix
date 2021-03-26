{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  # TODO: rename to pypiData with next major release
  inputs.pypi-deps-db = {
    url = "github:DavHau/pypi-deps-db";
    flake = false;
  };

  outputs = { self, nixpkgs, flake-utils, ... }@inp:
    let 
      dataOutdated =
        if inp.pypi-deps-db.sourceInfo ? lastModified
            && inp.nixpkgs.sourceInfo ? lastModified
            && inp.pypi-deps-db.sourceInfo.lastModified < inp.nixpkgs.sourceInfo.lastModified then
          true
        else
          false;
    in
      flake-utils.lib.eachDefaultSystem (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          mach-nix-default = import ./default.nix {inherit pkgs dataOutdated; };
        in rec
        {
          devShell = import ./shell.nix {
            inherit pkgs;
          };
          packages = flake-utils.lib.flattenTree rec {
            inherit (mach-nix-default)
              mach-nix
              pythonWith
              shellWith
              dockerImageWith;
            "with" = pythonWith;
            sdist = pkgs.runCommand "mach-nix-sdist"
              { buildInputs = mach-nix-default.pythonDeps; }
              ''
                mkdir src
                cp -r ${./.}/* src
                cd src
                python setup.py sdist -d $out
              '';
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
      );
}

{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "nixpkgs/nixos-unstable";
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
      usageGen = "usage: nix (build|shell) mach-nix#gen.(python|docker).package1.package2...";
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
            pypiData = "${inp.pypi-deps-db}";
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
                docker = mach-nix-default.dockerImageWith;
                inherit (mach-nix-default)
                  pythonWith
                  dockerImageWith;
              };
            };
          };

          defaultPackage = packages.mach-nix;

          apps.mach-nix = flake-utils.lib.mkApp { drv = packages.mach-nix.mach-nix; };
          apps.extract-reqs =
            let
              extractor = import ./lib/extractor {
                inherit pkgs;
                lib = inp.nixpkgs.lib;
              };
            in
            {
              type = "app";
              program = toString (pkgs.writeScript "extract.sh" ''
                export SRC=$1
                nix-build -o reqs -E 'let
                    pkgs = import <nixpkgs> {};
                    srcEnv = builtins.getEnv "SRC";
                    src = pkgs.copyPathToStore srcEnv;
                    srcTar = pkgs.runCommand "src.tar.gz" {} "mkdir src && cp -r ''${src}/* src/ && pwd && ls -la && tar -c src | gzip -1 > $out";
                  in (import ./lib/extractor {}).extract_from_src {
                    py="python3";
                    src = srcTar;
                  }'
                cat reqs/*
                rm reqs
              '');
            };

            apps.tests-unit = {
              type = "app";
              program = toString (pkgs.writeScript "tests-unit" ''
                export PATH="${pkgs.lib.makeBinPath (with pkgs; [
                  (import ./mach_nix/nix/python.nix {
                    inherit pkgs;
                    dev = true;
                  })
                ]
                ++ pkgs.lib.optional (stdenv.isLinux) busybox
                # This is not equivalent to "busybox", but is close enough for
                # everything to work. The only quirk here is borrowing a trick
                # from nixpkgs to provide a "/bin/sh" that's identical to the
                # one nixpkgs exists (coreutils doesn't bundle /bin/sh but
                # busybox does).
                ++ pkgs.lib.optionals (stdenv.isDarwin) [
                  coreutils
                  (pkgs.runCommand "bin-sh" {} "mkdir -p $out/bin && ln -s ${pkgs.bash}/bin/bash $out/bin/sh")
                ])}"

                export PYPI_DATA=${inp.pypi-deps-db}
                export CONDA_DATA=${(import ./mach_nix/nix/conda-channels.nix {
                  inherit pkgs;
                  providers = { _default = [ "conda/main" "conda/r" "conda/conda-forge"]; };
                }).condaChannelsJson}

                echo "executing unit tests"
                pytest -n $(nproc) -x ${./.}
              '');
            };

            apps.tests-eval = {
              type = "app";
              program = toString (pkgs.writeScript "tests-eval" ''
                export PATH="${pkgs.lib.makeBinPath (with pkgs; [
                  git
                  nixFlakes
                  parallel
                ]
                ++ pkgs.lib.optional (stdenv.isLinux) busybox
                ++ pkgs.lib.optionals (stdenv.isDarwin) [
                  coreutils
                  (pkgs.runCommand "bin-sh" {} "mkdir -p $out/bin && ln -s ${pkgs.bash}/bin/bash $out/bin/sh")
                ])}"

                cd tests
                echo "executing evaluation tests"
                ./execute.sh
              '');
            };

            apps.tests-all = {
              type = "app";
              program = toString (pkgs.writeScript "tests-eval" ''
                set -e
                ${apps.tests-unit.program}
                ${apps.tests-eval.program}
                CONDA_TESTS=y ${apps.tests-eval.program}
              '');
            };

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

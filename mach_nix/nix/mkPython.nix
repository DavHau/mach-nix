{ condaChannelsExtra, condaDataRev, condaDataSha256, pkgs, pypiDataRev, pypiDataSha256, ... }:

with builtins;
with pkgs.lib;
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  buildPythonPackageBase = (import ./buildPythonPackage.nix {
    inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs pypiDataRev pypiDataSha256;
   });

  mkPython = python:
    {
      requirements ? "",  # content from a requirements.txt file
      packagesExtra ? [], # add R-Packages, pkgs from nixpkgs, pkgs built via mach-nix.buildPythonPackage
      overridesPre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overridesPost ? [],  # list of pythonOverrides to apply after the machnix overrides
      providers ? {},  # define provider preferences
      tests ? false,  # Disable tests wherever possible to decrease build time.
      _ ? {},  # simplified overrides
      _providerDefaults ? with builtins; fromTOML (readFile ../provider_defaults.toml),
      _fixes ? import ../fixes.nix {pkgs = pkgs;}
    }:
    let
      python_pkg = l.selectPythonPkg pkgs python requirements;
      pyver = l.get_py_ver python_pkg;
      # and separate pkgs into groups
      extra_pkgs_python = map (p:
        # check if element is a package built via mach-nix
        if p ? pythomModule && ! p ? passthru._ then
          throw ''
            python packages from nixpkgs cannot be passed via `packagesExtra`.
            Instead, add the package's name to your `requirements` and set `providers.{package} = "nixpkgs"`
          ''
        else if p ? passthru._ then
          let
            pkg_pyver = l.get_py_ver p.pythonModule;
          in
            if pkg_pyver != pyver then
              throw ''
                ${p.pname} from 'packagesExtra' is built with python ${p.pythonModule.version},
                but the environment is based on python ${pyver.major}.${pyver.minor}.
                Please build ${p.pname} with 'python = "python${pyver.major}${pyver.minor}"'.
              ''
            else
              p
        # translate sources to python packages
        else
          buildPythonPackageBase python "buildPythonPackage" {
            inherit condaDataRev condaDataSha256 pkgs providers python
                    pypiDataRev pypiDataSha256 tests _providerDefaults;
            src = p;
          }
      ) (filter (p: l.is_src p || p ? pythonModule) packagesExtra);
      extra_pkgs_r = filter (p: p ? rCommand) packagesExtra;
      extra_pkgs_other = filter (p: ! (p ? rCommand || p ? pythonModule || l.is_src p)) packagesExtra;

      # gather requirements of exra pkgs
      extra_pkgs_py_reqs =
        map (p:
          if hasAttr "requirements" p then p.requirements
          else throw "Packages passed via 'packagesExtra' must be built via mach-nix.buildPythonPackage"
        ) extra_pkgs_python;
      extra_pkgs_r_reqs = if extra_pkgs_r == [] then "" else ''
        rpy2
        ipython
        jinja2
        pytz
        pandas
        numpy
        cffi
        tzlocal
        simplegeneric
      '';

      # gather overrides necessary by extra_pkgs
      extra_pkgs_python_attrs = foldl' (a: b: a // b) {} (map (p: { "${p.pname}" = p; }) extra_pkgs_python);
      extra_pkgs_py_overrides = [ (pySelf: pySuper: extra_pkgs_python_attrs) ];
      extra_pkgs_r_overrides = l.simple_overrides {
        rpy2.buildInputs.add = extra_pkgs_r;
      };
      overrides_simple_extra = flatten (
        (map l.simple_overrides (
          map (p: if hasAttr "_" p then p._ else {}) extra_pkgs_python
        ))
      );
      overrides_pre_extra = flatten (map (p: p.passthru.overridesPre) extra_pkgs_python);
      overrides_post_extra = flatten (map (p: p.passthru.overridesPost) extra_pkgs_python);

      py = python_pkg.override { packageOverrides = l.mergeOverrides overridesPre; };
      result = l.compileOverrides {
        inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs providers pypiDataRev pypiDataSha256 tests _providerDefaults;
        overrides = overridesPre ++ overrides_pre_extra ++ extra_pkgs_py_overrides;
        python = py;
        requirements = l.concat_reqs ([requirements] ++ extra_pkgs_py_reqs ++ [extra_pkgs_r_reqs]);
      };
      selectPkgs = ps:
        (result.select_pkgs ps)
        ++ (map (name: ps."${name}") (attrNames extra_pkgs_python_attrs));

      override_selectPkgs = pySelf: pySuper: {
        inherit selectPkgs;
      };

      all_overrides = l.mergeOverrides (
        overridesPre ++ overrides_pre_extra
        ++ extra_pkgs_py_overrides
        ++ [ (import ./mk-python-derivation-overlay.nix pkgs python_pkg) ]
        ++ [ result.overrides ]
        ++ (l.fixes_to_overrides _fixes)
        ++ overrides_post_extra ++ overridesPost
        ++ extra_pkgs_r_overrides
        ++ overrides_simple_extra ++ (l.simple_overrides _)
        ++ [ override_selectPkgs ]
      );
      py_final = python_pkg.override { packageOverrides = all_overrides;};
      py_final_with_pkgs = (py_final.withPackages (ps: selectPkgs ps)).overrideAttrs (oa:{
        postBuild = ''
          ${l.condaSymlinkJoin (flatten (map (p: p.allCondaDeps or []) (selectPkgs py_final.pkgs))) }
        '' + oa.postBuild;
      });
      final_env = py_final_with_pkgs.override (oa: {
        makeWrapperArgs = [
          ''--suffix-each PATH ":" "${toString (map (p: "${p}/bin") extra_pkgs_other)}"''
          ''--set QT_PLUGIN_PATH ${py_final_with_pkgs}/plugins''
        ];
      });
    in let
      self = final_env.overrideAttrs (oa: {
        passthru = oa.passthru // rec {
          inherit selectPkgs;
          pythonOverrides = all_overrides;
          python = py_final;
          env = pkgs.mkShell {
            name = "mach-nix-python-shell";
            buildInputs = [ final_env extra_pkgs_other ];
          };
          overlay = self: super:
            let
              py_attr_name = "python${pyver.major}${pyver.minor}";
            in
              {
                "${py_attr_name}" = super."${py_attr_name}".override {
                  packageOverrides = pythonOverrides;
                };
              };
          nixpkgs = import pkgs.path { config = pkgs.config; overlays = pkgs.overlays ++ [ overlay ]; };
          dockerImage = makeOverridable
            (args: pkgs.dockerTools.buildLayeredImage args)
            {
              name = "mach-nix-python";
              tag = "latest";
              contents = [
                pkgs.busybox
                self
              ] ++ extra_pkgs_other;
              config = {
                Cmd = [ "${self}/bin/python" ];
              };
            };
        };
      });
    in self;
in

python: args: mkPython python (l.translateDeprecatedArgs args)

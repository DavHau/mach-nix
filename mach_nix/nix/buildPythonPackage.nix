{ condaChannelsExtra, condaDataRev, condaDataSha256, pkgs, pypiDataRev, pypiDataSha256, ... }:

with builtins;
with pkgs.lib;
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  buildPythonPackageBase = python: func:
    args@{
      requirements ? null,  # content from a requirements.txt file
      requirementsExtra ? "",  # add additional requirements to the packge
      tests ? false,  # Disable tests wherever possible to decrease build time.
      extras ? [],
      doCheck ? tests,
      overridesPre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overridesPost ? [],  # list of pythonOverrides to apply after the machnix overrides
      passthru ? {},
      providers ? {},  # define provider preferences
      _ ? {},  # simplified overrides
      _providerDefaults ? with builtins; fromTOML (readFile ../provider_defaults.toml),
      _fixes ? import ../fixes.nix {pkgs = pkgs;},
      ...
    }:
    with (_buildPythonParseArgs args);
    with builtins;
    let
      python_arg = if isString python then python else throw '''python' must be a string. Example: "python38"'';
    in
    let
      python_pkg = pkgs."${python_arg}";
      src = l.get_src pass_args.src;
      # Extract dependencies automatically if 'requirements' is unset
      pname =
        if hasAttr "pname" args then args.pname
        else l.extract_meta python_pkg src "name" "pname";
      version =
        if hasAttr "version" args then args.version
        else l.extract_meta python_pkg src "version" "version";
      meta_reqs = l.extract_requirements python_pkg src "${pname}:${version}" extras;
      reqs =
        (if requirements == null then
          if builtins.hasAttr "format" args && args.format != "setuptools" then
            throw "Automatic dependency extraction is only available for 'setuptools' format."
                  " Please specify 'requirements' if setuptools is not used."
          else
            meta_reqs
        else
          requirements)
        + "\n" + requirementsExtra;
      py = python_pkg.override { packageOverrides = l.mergeOverrides overridesPre; };
      result = l.compileOverrides {
        inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs
                providers pypiDataRev pypiDataSha256 tests _providerDefaults;
        overrides = overridesPre;
        python = py;
        requirements = reqs;
      };
      py_final = python_pkg.override { packageOverrides = l.mergeOverrides (
        overridesPre
        ++ [ (import ./mk-python-derivation-overlay.nix pkgs python_pkg) ]
        ++ [ result.overrides ]
        ++ (l.fixes_to_overrides _fixes)
        ++ overridesPost ++ (l.simple_overrides _)
      );};
      pass_args = removeAttrs args (builtins.attrNames ({
        inherit condaDataRev condaDataSha256 overridesPre overridesPost pkgs providers
                requirements requirementsExtra pypiDataRev pypiDataSha256 python tests _providerDefaults _ ;
      }));
    in
    py_final.pkgs."${func}" ( pass_args // {
      propagatedBuildInputs =
        (result.select_pkgs py_final.pkgs)
        ++ (if hasAttr "propagatedBuildInputs" args then args.propagatedBuildInputs else []);
      src = src;
      inherit doCheck pname version;
      passthru = passthru // {
        requirements = reqs;
        inherit overridesPre overridesPost _;
      };
    });
in

python: func: args: buildPythonPackageBase python func (l.translateDeprecatedArgs args)

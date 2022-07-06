{ condaChannelsExtra, condaDataRev, condaDataSha256, pkgs, pypiData, ... }:

with builtins;
with pkgs.lib;
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  inherit (import ./extract-metadata.nix {
    inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs pypiData;
   }) extract-meta extract-requirements;

  buildPythonPackageBase = pythonGlobal: func:
    args@{
      cudaVersion ? pkgs.cudatoolkit.version,  # max allowed cuda version for conda packages
      ignoreDataOutdated ? false,  # don't fail if pypi data is older than nixpkgs
      requirements ? "",  # content from a requirements.txt file
      requirementsExtra ? "",  # add additional requirements to the packge
      tests ? false,  # Disable tests wherever possible to decrease build time.
      extras ? [],
      doCheck ? tests,
      overridesPre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overridesPost ? [],  # list of pythonOverrides to apply after the machnix overrides
      passthru ? {},
      providers ? {},  # define provider preferences
      python ? pythonGlobal,  # define python version
      _ ? {},  # simplified overrides
      _providerDefaults ? l.makeProviderDefaults requirements,
      _fixes ? import ../fixes.nix {pkgs = pkgs;},
      ...
    }:
    with builtins;
    let
      python_pkg = l.selectPythonPkg pkgs python requirements;
      src = l.get_src pass_args.src;
      # Extract dependencies automatically if 'requirements' is unset
      pname =
        if hasAttr "pname" args then args.pname
        else extract-meta { inherit python providers overridesPre src; } src "name" "pname";
      version =
        if hasAttr "version" args then args.version
        else extract-meta { inherit python providers overridesPre src; } src "version" "version";
      meta_reqs = extract-requirements { inherit python providers overridesPre src; } "${pname}:${version}" extras;
      reqs =
        (if requirements == "" then
            meta_reqs
        else
          requirements)
        + "\n" + requirementsExtra;
      py = python_pkg.override { packageOverrides = l.mergeOverrides overridesPre; };
      result = l.compileOverrides {
        inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs
                providers pypiData tests _providerDefaults;
        overrides = overridesPre;
        python = py;
        requirements = reqs;
      };
      py_final = python_pkg.override { packageOverrides = l.mergeOverrides (
        overridesPre
        ++ [ result.overrides ]
        ++ (l.fixes_to_overrides _fixes)
        ++ overridesPost ++ (l.simple_overrides _)
      );};
      pass_args = removeAttrs args (builtins.attrNames ({
        inherit condaDataRev condaDataSha256 overridesPre overridesPost pkgs providers
                requirements requirementsExtra pypiData tests _providerDefaults _ ;
      }));
    in
    py_final.pkgs."${func}" ( pass_args // {
      propagatedBuildInputs =
        (result.select_pkgs py_final.pkgs) ++ (args.propagatedBuildInputs or []);
      src = src;
      inherit doCheck pname version;
      passthru = passthru // {
        requirements = reqs;
        inherit overridesPre overridesPost _;
      };
    });
in

python: func: args: buildPythonPackageBase python func (l.translateDeprecatedArgs args)

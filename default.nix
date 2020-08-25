let
  pkgs = import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; overlays = []; };
  python = import ./mach_nix/nix/python.nix { inherit pkgs; };
  python_deps = (builtins.attrValues (import ./mach_nix/nix/python-deps.nix { inherit python; fetchurl = pkgs.fetchurl; }));
  mergeOverrides = with pkgs.lib; foldr composeExtensions (self: super: { });
  autoPatchelfHook = import ./mach_nix/nix/auto_patchelf_hook.nix {inherit (pkgs) fetchurl makeSetupHook writeText;};
  concat_reqs = reqs_list:
    let
      concat = s1: s2: s1 + "\n" + s2;
    in
      builtins.foldl' concat "" reqs_list;
  extractMeta = python: src: extras:
    with builtins;
    let
      file = (builtins.readFile "${(import ./lib/extractor).extract_from_src {
        py = python;
        src = src;
      }}/python.json");
      data = fromJSON file;
      setup_requires = if hasAttr "setup_requires" data then data.setup_requires else [];
      install_requires = if hasAttr "install_requires" data then data.install_requires else [];
      name = if hasAttr "name" data then data.name else null;
      version = if hasAttr "version" data then data.version else null;
      extras_require =
        if hasAttr "install_requires" data then
          pkgs.lib.flatten (map (extra: data.extras_require."${extra}") extras)
        else [];
      all_reqs = concat_reqs (setup_requires ++ install_requires ++ extras_require);
    in
      {
        requirements = trace "\n automatically detected requirements of ${name} ${version}:${all_reqs}\n\n" all_reqs;
        inherit name version;
      };
  is_http_url = url:
    with builtins;
    if (substring 0 8 url) == "https://" || (substring 0 7 url) == "http://" then true else false;
  get_src = src:
    with builtins;
    if isString src && is_http_url src then (fetchTarball src) else src;
in
rec {
  # the mach-nix cmdline tool derivation
  mach-nix = python.pkgs.buildPythonPackage rec {
    pname = "mach-nix";
    version = builtins.readFile ./mach_nix/VERSION;
    name = "${pname}-${version}";
    src = ./.;
    propagatedBuildInputs = python_deps;
    doCheck = false;
  };

  inherit mergeOverrides;

  # User might want to access it to choose python version
  nixpkgs = pkgs;

  # call this to generate a nix expression which contains the python overrides
  machNixFile = args: import ./mach_nix/nix/mach.nix args;

  # Returns `overrides` and `select_pkgs` which satisfy your requirements
  machNix = args:
    let
      result = import "${machNixFile args}/share/mach_nix_file.nix";
      manylinux =
        if pkgs.stdenv.hostPlatform.system == "x86_64-darwin" then
          []
        else
          pkgs.pythonManylinuxPackages.manylinux1;
    in {
      overrides = result.overrides manylinux autoPatchelfHook;
      select_pkgs = result.select_pkgs;
    };

  # call this to use the python environment with nix-shell
  mkPythonShell = args: (mkPython args).env;

  # equivalent to buildPythonPackage of nixpkgs
  buildPythonPackage = __buildPython "buildPythonPackage";

  # equivalent to buildPythonApplication of nixpkgs
  buildPythonApplication = __buildPython "buildPythonApplication";

  __buildPython = with builtins; func: args:
    if isString args || isPath args then _buildPython func { src = args; } else _buildPython func args;

  _buildPython = func: args@{
      add_requirements ? "",  # add additional requirements to the packge
      requirements ? null,  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      extras ? [],
      doCheck ? ! disable_checks,
      overrides_pre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overrides_post ? [],  # list of pythonOverrides to apply after the machnix overrides
      pkgs ? nixpkgs,  # pass custom nixpkgs.
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3,  # select custom python to base overrides onto. Should be from nixpkgs >= 20.03
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml),
      ...
    }:
    with builtins;
    let
      src = get_src pass_args.src;
      # Extract dependencies automatically if 'requirements' is unset
      meta = extractMeta python src extras;
      reqs =
        with builtins;
        (if requirements == null then
          if builtins.hasAttr "format" args && args.format != "setuptools" then
            throw "Automatic dependency extraction is only available for 'setuptools' format."
                  " Please specify 'requirements' if setuptools is not used."
          else
            meta.requirements
        else
          requirements) + "\n" + add_requirements;
      pname =
        if hasAttr "name" args then null
        else if hasAttr "pname" args then args.pname
        else meta.name;
      version =
        if hasAttr "name" args then null
        else if hasAttr "version" args then args.version
        else meta.version;
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit disable_checks providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        overrides = overrides_pre;
        python = py;
        requirements = reqs;
      };
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ [ result.overrides ] ++ overrides_post
      );};
      pass_args = removeAttrs args (builtins.attrNames ({
        inherit add_requirements disable_checks overrides_pre overrides_post pkgs providers
                requirements pypi_deps_db_commit pypi_deps_db_sha256 python _provider_defaults;
      }));
    in
    py_final.pkgs."${func}" ( pass_args // {
      propagatedBuildInputs = result.select_pkgs py_final.pkgs;
      src = src;
      inherit doCheck pname version;
      passthru = {
        requirements = reqs;
      };
    });


  # (High level API) generates a python environment with minimal user effort
  mkPython = args: if builtins.isList args then _mkPython { extra_pkgs = args; } else _mkPython args;

  _mkPython =
    {
      requirements ? "",  # content from a requirements.txt file
      disable_checks ? true,  # Disable tests wherever possible to decrease build time.
      extra_pkgs ? [],
      overrides_pre ? [],  # list of pythonOverrides to apply before the machnix overrides
      overrides_post ? [],  # list of pythonOverrides to apply after the machnix overrides
      pkgs ? nixpkgs,  # pass custom nixpkgs.
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3,  # select custom python to base overrides onto. Should be from nixpkgs >= 20.03
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml)
    }:
    with builtins;
    let
      _extra_pkgs = map (p: if isString p || isPath p then buildPythonPackage p else p) extra_pkgs;
      extra_pkgs_reqs =
        map (p:
          if builtins.hasAttr "requirements" p then p.requirements
          else throw "Packages passed via 'extra_pkgs' must be built via mach-nix.buildPythonPackage"
        ) _extra_pkgs;
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit disable_checks providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        overrides = overrides_pre;
        python = py;
        requirements = concat_reqs ([requirements] ++ extra_pkgs_reqs);
      };
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ [ result.overrides ] ++ overrides_post
      );};
    in
      py_final.withPackages (ps: (result.select_pkgs ps) ++ _extra_pkgs)
    ;
}

with builtins;
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
  extract = python: src: fail_msg:
    let
      file_path = "${(import ./lib/extractor).extract_from_src {
          py = python;
          src = src;
        }}/python.json";
    in
      if pathExists file_path then fromJSON (readFile file_path) else throw fail_msg;
  extractRequirements = python: src: name: extras:
     with pkgs.lib;
    let
      data = extract python src ''
        Automatic requirements extraction failed for ${name}.
        Please manually specify 'requirements' '';
      setup_requires = if hasAttr "setup_requires" data then data.setup_requires else [];
      install_requires = if hasAttr "install_requires" data then data.install_requires else [];
      extras_require =
        if hasAttr "extras_require" data then
          pkgs.lib.flatten (map (extra: data.extras_require."${extra}") extras)
        else [];
      all_reqs = concat_reqs (setup_requires ++ install_requires ++ extras_require);
      msg = "\n automatically detected requirements of ${name} ${version}:${all_reqs}\n\n";
    in
      trace msg all_reqs;
  extractMeta = python: src: attr:
    with pkgs.lib;
    let
      error_msg = ''
        Automatic extraction of '${attr}' from python package source ${src} failed.
        Please manually specify '${attr}' '';
      data = extract python src error_msg;
      result = if hasAttr attr data then data."${attr}" else throw error_msg;
      msg = "\n automatically detected ${attr}: '${result}'";
    in
      trace msg result;
  is_http_url = url:
    with builtins;
    if (substring 0 8 url) == "https://" || (substring 0 7 url) == "http://" then true else false;
  get_src = src:
    with builtins;
    if isString src && is_http_url src then (fetchTarball src) else src;
  combine = val1: val2:
    if isList val2 then val1 ++ val2
    else if isAttrs val2 then val1 // val2
    else if isString val2 then val1 + val2
    else throw "_.${pkg}.${key}.add only accepts list or attrs or string.";
  meets_cond = oa: condition:
    let
      provider = if hasAttr "provider" oa then oa.provider else "nixpkgs";
    in
    condition { prov = provider; ver = oa.version; pyver = oa.pythonModule.version; };
  simple_overrides = args: with pkgs.lib;
    flatten (
      mapAttrsToList (pkg: keys:
        mapAttrsToList (key: val:
          if isAttrs val && hasAttr "add" val then
            pySelf: pySuper:
              let combine =
                if isList val.add then (a: b: a ++ b)
                else if isAttrs val.add then (a: b: a // b)
                else if isString val.add then (a: b: a + b)
                else throw "_.${pkg}.${key}.add only accepts list or attrs or string.";
              in {
                "${pkg}" = pySuper."${pkg}".overrideAttrs (oa: {
                  "${key}" = combine oa."${key}" val.add;
                });
              }
          else if isAttrs val && hasAttr "mod" val && isFunction val.mod then
            pySelf: pySuper: {
              "${pkg}" = pySuper."${pkg}".overrideAttrs (oa: {
                "${key}" = val.mod oa."${key}";
              });
            }
          else pySelf: pySuper: {
            "${pkg}" = pySuper."${pkg}".overrideAttrs (oa: {
              "${key}" = val;
            });
          }
        ) keys
      ) args
    );
  fixes_to_overrides = fixes: with pkgs.lib;
    flatten (flatten (
      mapAttrsToList (pkg: p_fixes:
        mapAttrsToList (fix: keys: pySelf: pySuper:
          let cond = if hasAttr "_cond" keys then keys._cond else ({prov, ver, pyver}: true); in
          if ! hasAttr "${pkg}" pySuper then {} else
          {
            "${pkg}" = pySuper."${pkg}".overrideAttrs (oa:
              mapAttrs (key: val:
                if ! meets_cond oa cond then
                  oa."${key}"
                else trace "\napplying fix '${fix}' for ${pkg}:${oa.version}\n" (
                  if isAttrs val && hasAttr "add" val then
                    combine oa."${key}" val.add
                  else if isAttrs val && hasAttr "mod" val && isFunction val.mod then
                    val.mod oa."${key}"
                  else
                    val
                )
              ) (filterAttrs (k: v: k != "_cond") keys)
            );
          }
        ) p_fixes
      ) fixes
    ));
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
      result = import "${machNixFile (removeAttrs args [ "pkgs" ])}/share/mach_nix_file.nix";
      manylinux =
        if args.pkgs.stdenv.hostPlatform.system == "x86_64-darwin" then
          []
        else
          args.pkgs.pythonManylinuxPackages.manylinux1;
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
      passthru ? {},
      pkgs ? nixpkgs,  # pass custom nixpkgs.
      providers ? {},  # define provider preferences
      pypi_deps_db_commit ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_COMMIT,  # python dependency DB version
      pypi_deps_db_sha256 ? builtins.readFile ./mach_nix/nix/PYPI_DEPS_DB_SHA256,
      python ? pkgs.python3,  # select custom python to base overrides onto. Should be from nixpkgs >= 20.03
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml),
      _ ? {},  # simplified overrides
      ...
    }:
    with builtins;
    let
      python_arg = python;
    in
    let
      python = if isString python_arg then pkgs."${python_arg}" else python_arg;
      src = get_src pass_args.src;
      # Extract dependencies automatically if 'requirements' is unset
      meta_name = extractMeta python src "name";
      meta_version = extractMeta python src "version";
      pname =
        if hasAttr "name" args then null
        else if hasAttr "pname" args then args.pname
        else meta_name;
      version =
        if hasAttr "name" args then null
        else if hasAttr "version" args then args.version
        else meta_version;
      meta_reqs = extractRequirements python src (if isNull pname then args.name else "${pname}:${version}") extras;
      reqs =
        (if requirements == null then
          if builtins.hasAttr "format" args && args.format != "setuptools" then
            throw "Automatic dependency extraction is only available for 'setuptools' format."
                  " Please specify 'requirements' if setuptools is not used."
          else
            meta_reqs
        else
          requirements)
        + "\n" + add_requirements;
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit disable_checks pkgs providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        overrides = overrides_pre;
        python = py;
        requirements = reqs;
      };
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ [ result.overrides ] ++ overrides_post ++ (simple_overrides _)
      );};
      pass_args = removeAttrs args (builtins.attrNames ({
        inherit add_requirements disable_checks overrides_pre overrides_post pkgs providers
                requirements pypi_deps_db_commit pypi_deps_db_sha256 python _provider_defaults _ ;
      }));
    in
    py_final.pkgs."${func}" ( pass_args // {
      propagatedBuildInputs = result.select_pkgs py_final.pkgs;
      src = src;
      inherit doCheck pname version;
      passthru = passthru // {
        requirements = reqs;
        inherit overrides_pre overrides_post _;
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
      _ ? {},  # simplified overrides
      _provider_defaults ? with builtins; fromTOML (readFile ./mach_nix/provider_defaults.toml),
      _fixes ? import ./mach_nix/fixes.nix {pkgs = pkgs;}
    }:
    with builtins;
    with pkgs.lib;
    let
      python_arg = python;
    in
    let
      python = if isString python_arg then pkgs."${python_arg}" else python_arg;
      _extra_pkgs = map (p:
        if isString p || isPath p then
          _buildPython "buildPythonPackage" {
            src = p;
            inherit disable_checks pkgs providers pypi_deps_db_commit pypi_deps_db_sha256 python _provider_defaults;
          }
        else p
      ) extra_pkgs;
      extra_pkgs_reqs =
        map (p:
          if hasAttr "requirements" p then p.requirements
          else throw "Packages passed via 'extra_pkgs' must be built via mach-nix.buildPythonPackage"
        ) _extra_pkgs;
      overrides_simple_extra = flatten (
        (map simple_overrides (
          map (p: if hasAttr "_" p then p._ else {}) _extra_pkgs
        ))
      );
      overrides_pre_extra = flatten (map (p: p.passthru.overrides_pre) _extra_pkgs);
      overrides_post_extra = flatten (map (p: p.passthru.overrides_post) _extra_pkgs);
      py = python.override { packageOverrides = mergeOverrides overrides_pre; };
      result = machNix {
        inherit disable_checks pkgs providers pypi_deps_db_commit pypi_deps_db_sha256 _provider_defaults;
        overrides = overrides_pre;
        python = py;
        requirements = concat_reqs ([requirements] ++ extra_pkgs_reqs);
      };
      py_final = python.override { packageOverrides = mergeOverrides (
        overrides_pre ++ overrides_pre_extra
        ++ [ result.overrides ]
        ++ (fixes_to_overrides _fixes)
        ++ overrides_post_extra ++ overrides_post
        ++ overrides_simple_extra ++ (simple_overrides _)
      );};
    in
      py_final.withPackages (ps: (result.select_pkgs ps) ++ _extra_pkgs)
    ;
}

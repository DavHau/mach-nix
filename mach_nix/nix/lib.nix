{ lib, pkgs, ... }:
with builtins;
with lib;
rec {

  mergeOverrides = foldl composeExtensions (self: super: { });

  autoPatchelfHook = import ./auto_patchelf_hook.nix {inherit (pkgs) fetchurl makeSetupHook writeText;};

  concat_reqs = reqs_list:
    let
      concat = s1: s2: s1 + "\n" + s2;
    in
      builtins.foldl' concat "" reqs_list;

  # call this to generate a nix expression which contains the mach-nix overrides
  compileExpression = args: import ./compileOverrides.nix args;

  # Returns `overrides` and `select_pkgs` which satisfy your requirements
  compileOverrides = args:
    let
      result = import "${compileExpression args}/share/mach_nix_file.nix" { inherit (args) pkgs python; };
      manylinux =
        if args.pkgs.stdenv.hostPlatform.system == "x86_64-darwin" then
          []
        else
          args.pkgs.pythonManylinuxPackages.manylinux1;
    in {
      overrides = result.overrides manylinux autoPatchelfHook;
      select_pkgs = result.select_pkgs;
    };

  meets_cond = oa: condition:
    let
      provider = if hasAttr "provider" oa.passthru then oa.passthru.provider else "nixpkgs";
    in
      condition { prov = provider; ver = oa.version; pyver = oa.pythonModule.version; };

    extract = python: src: fail_msg:
    let
      file_path = "${(import ../../lib/extractor { inherit pkgs; }).extract_from_src {
          py = python;
          src = src;
        }}/python.json";
    in
      if pathExists file_path then fromJSON (readFile file_path) else throw fail_msg;

  extract_requirements = python: src: name: extras:
    let
      ensureList = requires: if isString requires then [requires] else requires;
      data = extract python src ''
        Automatic requirements extraction failed for ${name}.
        Please manually specify 'requirements' '';
      setup_requires = if hasAttr "setup_requires" data then ensureList data.setup_requires else [];
      install_requires = if hasAttr "install_requires" data then ensureList data.install_requires else [];
      extras_require =
        if hasAttr "extras_require" data then
          flatten (map (extra: data.extras_require."${extra}") extras)
        else [];
      all_reqs = concat_reqs (setup_requires ++ install_requires ++ extras_require);
      msg = "\n automatically detected requirements of ${name} ${version}:${all_reqs}\n\n";
    in
      trace msg all_reqs;

  extract_meta = python: src: attr: for_attr:
    let
      error_msg = ''
        Automatic extraction of '${for_attr}' from python package source ${src} failed.
        Please manually specify '${for_attr}' '';
      data = extract python src error_msg;
      result = if hasAttr attr data then data."${attr}" else throw error_msg;
      msg = "\n automatically detected ${for_attr}: '${result}'";
    in
      trace msg result;

  is_src = input: ! input ? passthru;

  is_http_url = url:
    with builtins;
    if (substring 0 8 url) == "https://" || (substring 0 7 url) == "http://" then true else false;

  get_src = src:
    with builtins;
    if isString src && is_http_url src then (fetchTarball src) else src;

  get_py_ver = python: {
    major = elemAt (splitString "." python.version) 0;
    minor = elemAt (splitString "." python.version) 1;
  };

  combine = pname: key: val1: val2:
    if isList val2 then val1 ++ val2
    else if isAttrs val2 then val1 // val2
    else if isString val2 then val1 + val2
    else throw "_.${pname}.${key}.add only accepts list or attrs or string.";

  fixes_to_overrides = fixes:
    flatten (flatten (
      mapAttrsToList (pkg: p_fixes:
        mapAttrsToList (fix: keys: pySelf: pySuper:
          let cond = if hasAttr "_cond" keys then keys._cond else ({prov, ver, pyver}: true); in
          if ! hasAttr "${pkg}" pySuper then {} else
          {
            "${pkg}" = pySuper."${pkg}".overrideAttrs (oa:
              mapAttrs (key: val:
                trace "\napplying fix '${fix}' (${key}) for ${pkg}:${oa.version}\n" (
                  if isAttrs val && hasAttr "add" val then
                    combine pkg key oa."${key}" val.add
                  else if isAttrs val && hasAttr "mod" val && isFunction val.mod then
                    let result = val.mod oa."${key}"; in
                      # if the mod function wants more argument, call with more arguments (alternative style)
                      if ! isFunction result then
                        result
                      else
                          val.mod pySelf oa oa."${key}"
                  else
                    val
                )
              ) (filterAttrs (k: v: k != "_cond" && meets_cond oa cond) keys)
            );
          }
        ) p_fixes
      ) fixes
    ));

  simple_overrides = args:
    flatten ( mapAttrsToList (pkg: keys: pySelf: pySuper: {
      "${pkg}" = pySuper."${pkg}".overrideAttrs (oa:
        mapAttrs (key: val:
          if isAttrs val && hasAttr "add" val then
            combine pkg key oa."${key}" val.add
          else if isAttrs val && hasAttr "mod" val && isFunction val.mod then
            let result = val.mod oa."${key}"; in
              # if the mod function wants more argument, call with more arguments (alternative style)
              if ! isFunction result then
                result
              else
                val.mod pySelf oa oa."${key}"
          else
            val
        ) keys
      );
    }) args);

  translateDeprecatedArgs = args:
    let
      aliases = import ./aliases.nix;
    in
      mapAttrs' (k: v:
        if aliases ? translate."${k}" then
          let
            newName = aliases.translate."${k}";
            newVal = if aliases ? transform."${k}" then aliases.transform."${k}" v else v;
          in
            trace ''
              DEPRECATION WARNING: Argument '${k}' is deprecated and might be removed in a future version.
              Please use '${newName}' instead.
            ''
            nameValuePair newName newVal
        else
          nameValuePair k v
      ) args;

  throwOnDeprecatedArgs = func: args:
    let
      moved = {
        pkgs = "pkgs";
        python = "python";
        pypi_deps_db_commit = "pypiDataRev";
        pypi_deps_db_sha256 = "pypiDataSha256";
      };
    in
      mapAttrs' (k: v:
        if moved ? "${k}" then
          throw ''${func} does not accept '${k}' anymore. Instead, provide '${moved."${k}"}' when importing mach-nix.''
        else
          nameValuePair k v
      ) args;
}

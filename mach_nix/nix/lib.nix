{
  pkgs ? import (import ./nixpkgs-src.nix) { config = {}; overlays = []; },
  ...
}:
with builtins;
with pkgs.lib;
let
  nonCondaProviders = [
    "wheel"
    "sdist"
    "nixpkgs"
  ];
in
rec {

  autoPatchelfHook = import ./auto_patchelf_hook.nix {inherit (pkgs) fetchurl makeSetupHook writeText;};

  mergeOverrides = foldl composeExtensions (self: super: { });

  fromYAML = str:
    fromJSON (readFile (pkgs.runCommand "yml" { buildInputs = [pkgs.yq pkgs.jq] ;} ''echo '${escape ["'"] str}' | ${pkgs.yq}/bin/yq . > $out''));

  isCondaEnvironmentYml = str: hasInfix "\nchannels:\n" str && hasInfix "\ndependencies:\n" str;

  condaSymlinkJoin = ps:
    let
      dirsForLinking = pkg:
        let
          dirs = filterAttrs (dir: type:
            ! elem dir [ "bin" "lib" "shared" ]
            && type != "regular"
          ) (readDir "${pkg}");
        in
          attrNames dirs;

      linkMap = ps: foldl (dirMap: pkg:
        dirMap // listToAttrs (map (dir:
          nameValuePair dir ((dirMap."${dir}" or []) ++ [ pkg ] )
        ) (dirsForLinking pkg))
      ) {} ps;

      linkCommand = dir: ps: ''
        if [ -e "$out/${dir}" ]; then
          mv "$out/${dir}" "$out/${dir}-self"
        fi
        ln -s "${pkgs.symlinkJoin {
          name = dir;
          paths = map (p: "${p}/${dir}") ps;
        }}" "$out/${dir}-deps"
        rm -f "$out/${dir}"
        mkdir "$out/${dir}"
        find "$out/${dir}-deps/" -mindepth 1 -maxdepth 1 -exec sh -c '
          ln -s "{}" "$out/${dir}/$(basename {})"
        ' \;
        if [ -e "$out/${dir}-self" ]; then
          find "$out/${dir}-self/" -mindepth 1 -maxdepth 1 -exec sh -c '
            [ ! -e "$out/${dir}/$(basename {})" ] && ln -s "{}" "$out/${dir}/$(basename {})"
          ' \;
        fi
      '';
      lMap = linkMap ps;
    in
      concatStringsSep "\n" (mapAttrsToList (dir: ps: linkCommand dir ps) lMap);

  selectPythonPkg = pkgs: pyStr: requirements:
    let
      preProcessedReqs = (preProcessRequirements requirements);
      python_arg =
        (if isString pyStr || isNull pyStr then
          pyStr
         else
          throw '''python' must be a string. Example: "python38"'');
    in
      if preProcessedReqs ? python then
        if ! isNull pyStr && pyStr != preProcessedReqs.python then
          throw ''
            The specified 'python' conflicts the one specified via 'requirements'.
            Either remove `python=` from your requirements or do not specify 'python' when importing mach-nix
          ''
        else
          pkgs."${preProcessedReqs.python}"
      else if isNull pyStr then
        pkgs.python3
      else
        pkgs."${python_arg}" ;

  preProcessRequirements = str:
    let
     condaYml2reqs = data:
      {
        requirements =
          concatStringsSep "\n" (flatten (map (d:
            let
              split = splitString "=" d;
              name = elemAt split 0;
              ver = elemAt split 1;
              build = elemAt split 2;
              build'=
                if isNull (match "py[[:digit:]]+_[[:digit:]]+" build) && isNull (match "[[:digit:]]+" build) then
                  build
                else
                  "*";
            in
              if hasPrefix "_" name || elem name [ "python" "conda" ] then
                []
              else
                "${name} ${ver} ${build'}"
          ) data.dependencies));

        providers = flatten (map (c:
          if c == "defaults" then
            [ "conda/main" "conda/r" ]
          else
            "conda/" + c
        ) data.channels);
      } // (
        let
          pyDep = filter (d: hasPrefix "python=" d) data.dependencies;
        in
          if pyDep == [] then {}
          else let
            pyVer = splitString "." (elemAt (splitString "=" (elemAt pyDep 0)) 1); # example: [ 3 7 2 ]
          in
            { python = "python${elemAt pyVer 0}${elemAt pyVer 1}"; }
      );
    in
      if isCondaEnvironmentYml str then
        condaYml2reqs (fromYAML str)
      else {
        requirements = str;
        providers = [];
      };

  parseProviders = providers:
    let
      # transform strings to lists
      _providers = mapAttrs (pkg: providers:
        if isString providers then
          splitString "," providers
        else providers
      ) providers;
    in
      # convert "some-conda-channel" to "conda/some-conda-channel"
      mapAttrs (pkg: providers:
        flatten (map (p:
          if elem p nonCondaProviders || hasPrefix "conda/" p then
            p
          else if p == "conda" then
            [ "conda/main" "conda/r" ]
          else
            "conda/${p}"
        ) providers)
      ) _providers;

  parseProvidersToJson =
    let
      providers = (fromJSON (getEnv "providers"));
    in
      pkgs.writeText "providers-json" (toJSON (parseProviders providers));

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
      file = "${compileExpression args}/share/mach_nix_file.nix";
      result = import file { inherit (args) pkgs python; };
      manylinux =
        if args.pkgs.stdenv.hostPlatform.system == "x86_64-darwin" then
          []
        else
          args.pkgs.pythonManylinuxPackages.manylinux1;
    in {
      overrides = result.overrides manylinux autoPatchelfHook;
      select_pkgs = result.select_pkgs;
      expr = readFile file;
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

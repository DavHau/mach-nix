{pkgs, python, mergeOverrides, overrides}:

let
  pnamePassthruOverride = pySelf: pySuper: {
    fetchPypi = args: (pySuper.fetchPypi args).overrideAttrs (oa: {
      passthru = { inherit (args) pname; };
    });
  };

  nameMap = {
    pytorch = "torch";
  };

  py = python.override { packageOverrides = mergeOverrides ( overrides ++ [ pnamePassthruOverride ] ); };
in

with pkgs;
with lib;
with builtins;
let
  pname_and_version = python: attrname:
    let
      pname = get_pname python.pkgs."${attrname}";
      res = tryEval (
        if pname != "" && hasAttrByPath ["${attrname}" "version"] python.pkgs
        then pname + "@" + (toString python.pkgs."${attrname}".version)
        else "N/A"
      );
    in
      {"${attrname}" = (toString res.value);};

  get_pname = pkg:
    let
      res = tryEval (
        if pkg ? src.pname then
          pkg.src.pname
        else if pkg ? pname then
          let pname = pkg.pname; in
            if nameMap ? "${pname}" then nameMap."${pname}" else pname
          else ""
      );
    in
      toString res.value;

  not_usable = pkg:
    (tryEval (
      if pkg == null
      then true
      else if hasAttrByPath ["meta" "broken"] pkg
      then pkg.meta.broken
      else false
    )).value;

  usable_pkgs = python_pkgs: filterAttrs (name: val: ! (not_usable val)) python_pkgs;
  all_pkgs = python: map (pname: pname_and_version python pname) (attrNames (usable_pkgs python.pkgs));
  merged = python: mapAttrs (name: val: elemAt val 0) (zipAttrs (all_pkgs python));
in
writeText "nixpkgs-py-pkgs-json" (toJSON (merged py))

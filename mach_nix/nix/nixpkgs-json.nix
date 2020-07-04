{pkgs, python}:
with pkgs;
with builtins;
with lib;
let
  get_version = python: pname:
    let
      res = tryEval (
        if hasAttrByPath ["${pname}" "version"] python.pkgs
        then python.pkgs."${pname}".version
        else "N/A"
      );
    in
      {"${pname}" = (toString res.value);};

  not_usable = pkg:
    (tryEval (
      if pkg == null
      then true
      else if hasAttrByPath ["meta" "broken"] pkg
      then pkg.meta.broken
      else false
    )).value;


  usable_pkgs = python_pkgs: filterAttrs (name: val: ! (not_usable val)) python_pkgs;
  all_versions = python: map (pname: get_version python pname) (attrNames (usable_pkgs python.pkgs));
  merged = python: mapAttrs (name: val: elemAt val 0) (zipAttrs (all_versions python));
in
writeText "nixpkgs-py-pkgs-json" (toJSON (merged python))

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

  is_broken = pkg:
    (tryEval (
      if hasAttrByPath ["meta" "broken"] pkg
      then pkg.meta.broken
      else false
    )).value;


  without_broken = python_pkgs: filterAttrs (name: val: ! (is_broken val)) python_pkgs;
  all_versions = python: map (pname: get_version python pname) (attrNames (without_broken python.pkgs));
  merged = python: mapAttrs (name: val: builtins.elemAt val 0) (zipAttrs (all_versions python));
in
writeText "nixpkgs-py-pkgs-json" (builtins.toJSON (merged python))

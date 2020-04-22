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

  all_versions = python: map (pname: get_version python pname) (attrNames python.pkgs);
  merged = python: mapAttrs (name: val: builtins.elemAt val 0) (zipAttrs (all_versions python));
in
writeText "nixpkgs-py-pkgs-json" (builtins.toJSON (merged python))

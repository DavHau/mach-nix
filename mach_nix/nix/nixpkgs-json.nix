{pkgs, python, mergeOverrides, overrides}:
let
  fetchPypiPnamePassthruOverride = pySelf: PySuper: {
    fetchPypi = let
      computeUrl = {format ? "setuptools", ... } @attrs: let
        computeWheelUrl = {pname, version, python ? "py2.py3", abi ? "none", platform ? "any"}:
          "https://files.pythonhosted.org/packages/${python}/${builtins.substring 0 1 pname}/${pname}/${pname}-${version}-${python}-${abi}-${platform}.whl";
        computeSourceUrl = {pname, version, extension ? "tar.gz"}:
          "mirror://pypi/${builtins.substring 0 1 pname}/${pname}/${pname}-${version}.${extension}";
        compute = (if format == "wheel" then computeWheelUrl
          else if format == "setuptools" then computeSourceUrl
          else throw "Unsupported format ${format}");
      in compute (builtins.removeAttrs attrs ["format"]);
    in pkgs.makeOverridable( {format ? "setuptools", sha256 ? "", hash ? "", ... } @attrs:
      let
        url = computeUrl (builtins.removeAttrs attrs ["sha256" "hash"]) ;
      in pkgs.fetchurl {
        inherit url sha256 hash;
        passthru = {
          inherit (attrs) pname;
        };
      });
  };

  py = python.override { packageOverrides = mergeOverrides ( overrides ++ [ fetchPypiPnamePassthruOverride ] ); };
in

with pkgs;
with lib;
with builtins;
let
  pname_and_version = python: attrname:
    let
      pname = get_pname python attrname;
      res = tryEval (
        if pname != "" && hasAttrByPath ["${attrname}" "version"] python.pkgs
        then pname + "@" + (toString python.pkgs."${attrname}".version)
        else "N/A"
      );
    in
      {"${attrname}" = (toString res.value);};

  get_pname = python: attrname:
    let
      res = tryEval (
        if hasAttrByPath ["${attrname}" "src" "pname"] python.pkgs then
          python.pkgs."${attrname}".src.pname
        else if hasAttrByPath ["${attrname}" "pname"] python.pkgs then
          python.pkgs."${attrname}".pname
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

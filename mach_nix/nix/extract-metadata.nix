{ condaChannelsExtra, condaDataRev, condaDataSha256, pkgs, pypiData, ... }:
with builtins;
with pkgs.lib;
let
  l = import ./lib.nix { inherit (pkgs) lib; inherit pkgs; };

  mkPython = (import ./mkPython.nix {
    inherit condaChannelsExtra condaDataRev condaDataSha256 pkgs pypiData;
  });
  default-build-system = {
    requires = ["setuptools >= 40.8.0" "wheel"];
    build-backend = "setuptools.build_meta:__legacy__";
  };

  extract-cmd = {python, src, providers, overridesPre}: outPath:
    let
      pyproject-toml = "${src}/pyproject.toml";
      build-system = if builtins.pathExists pyproject-toml then
          let
            toml = builtins.fromTOML (builtins.readFile pyproject-toml);
          in toml.build-system
        else default-build-system;
      base-env = mkPython python {
        inherit python providers;
        requirements = ''
          pep517
          importlib-metadata >= 4.0.0
        '';
      };
      build-env = mkPython python {
        inherit python providers overridesPre;
        requirements = concatStringsSep "\n" build-system.requires;
      };
      args = escapeShellArgs [build-env.interpreter build-system.build-backend build-system.backend-path or ""];
    in 
      ''
      ${base-env.interpreter} ${./extract-metadata.py} ${outPath} ${src} ${args}
      '';

    extract = {python, src, providers, overridesPre}@args: fail_msg:
      let
        result = pkgs.runCommand "python-metadata" {} ''
          mkdir $out
          ${extract-cmd args "$out/python.json"}
        '';
        file_path = traceVal "${result}/python.json";
      in
        if pathExists file_path then fromJSON (readFile file_path) else throw fail_msg;

    extract-requirements = {python, src, providers, overridesPre}@args: name: extras:
      let
        ensureList = requires: if isString requires then [requires] else requires;
        data = extract args ''
          Automatic requirements extraction failed for ${name}.
          Please manually specify 'requirements' '';
        setup_requires = if hasAttr "setup_requires" data then ensureList data.setup_requires else [];
        install_requires = if hasAttr "requires_dist" data then ensureList data.requires_dist else [];
        extras_require =
          if hasAttr "extras_require" data then
            flatten (map (extra: data.extras_require."${extra}") extras)
          else [];
        all_reqs = l.concat_reqs (setup_requires ++ install_requires ++ extras_require);
        msg = "\n automatically detected requirements of ${name} ${version}:${all_reqs}\n\n";
      in
        trace msg all_reqs;

    extract-meta = {python, src, providers, overridesPre}@args: attr: for_attr:
      let
        error_msg = ''
          Automatic extraction of '${for_attr}' from python package source ${src} failed.
          Please manually specify '${for_attr}' '';
        data = extract args error_msg;
        result = if hasAttr attr data then data."${attr}" else throw error_msg;
        msg = "\n automatically detected ${for_attr}: '${result}'";
      in
        trace msg result;
in {
  inherit extract-cmd extract-meta extract-requirements;
}

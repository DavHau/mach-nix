{ pkgs }:
with builtins;
with pkgs.lib;

# some basic helper functions
let

  # evaluate arbitrary python expression and return json parsed result
  py_eval = str: fromJSON ( readFile (
    pkgs.runCommand "py-eval-result" { buildInputs = with pkgs; [ python python3Packages.packaging ]; } ''
      ${pkgs.python}/bin/python -c "${str}" > $out
    ''));

  # compare two python versions
  # example: comp_ver "1.2.3" "<=" "2.0.4.dev0"
  # return type: bool
  comp_ver = ver1: op: ver2: py_eval ''
    import json
    from packaging.version import Version, parse
    result = parse('${ver1}') ${op} parse('${ver2}')
    print(json.dumps(result))
  '';
in


### Put Fixes here
rec {

###  FORMAT  ############################################################################
#                                                                                       #
#   package-to-fix = {                                                                  #
#     name-of-the-fix = {                                                               #
#       # optionally limit the fix to a condtion                                        #
#       _cond = {prov, ver, ... }: some boolean expression;                             #
#                                                                                       #
#       # define overrides                                                              #
#       key-to-override = ...;                                 # replace                #
#       key-to-override.add = ...;                             # append                 #
#       key-to-override.mod = oldVal: ...;                     # modify                 #
#       key-to-override.mod = pySelf: oldAttrs: oldVal: ...;   # modify (more args)     #
#     };                                                                                #
#   };                                                                                  #
#                                                                                       #
#########################################################################################

### _cond ####################################
#  possible arguments:                       #
#   - prov  (provider of the package)        #
#   - ver   (version of the package)         #
#   - pyver (python version used)            #
##############################################

  ldap0.add-inputs = {
    buildInputs.add = with pkgs; [ openldap.dev cyrus_sasl.dev ];
  };

  mariadb.add-mariadb-connector-c = {
    _cond = { prov, ... }: trace "cdsacdsac\ncdsdca\n" prov != "nixpkgs";
    MARIADB_CONFIG = "${pkgs.mariadb-connector-c}/bin/mariadb_config";
  };

  orange3.skipFixup = {
    dontFixup = true;
  };

  pip.remove-reproducible-patch = {
    _cond = { prov, ver, ... }: prov == "sdist" && comp_ver ver "<" "20.0";
    patches.mod = oldPatches: filter (patch: ! hasSuffix "reproducible.patch" patch) oldPatches;
  };

  pyqt5 = {
    fix-build-inputs = {
      # fix mach-nix induced problem: mach-nix removes all previous python inputs from propagatedBuildInputs
      _cond = {prov, ... }: prov == "nixpkgs";
      propagatedBuildInputs.mod = pySelf: oldAttrs: oldVal:
        (filter (p: p.pname != "pyqt5-sip") oldVal) ++ [ pySelf.sip pySelf.dbus-python ];
    };
    fix-wheel-inputs = {
      _cond = {prov, ... }: prov == "wheel";
      buildInputs.mod = pySelf: oldAttrs: oldVal:
        oldVal ++ pkgs.python3Packages.pyqt5.buildInputs ++ [ pkgs.kerberos pySelf.sip ];
    };
  };

  tensorflow.rm-tensorboard = {
    _cond = {prov, ... }: prov != "nixpkgs";
    postInstall = "rm $out/bin/tensorboard";
  };

  tensorflow-gpu = tensorflow;

}
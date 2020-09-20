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

###  FORMAT  ###########################################################
#                                                                      #
#   package-to-fix = {                                                 #
#     name-of-the-fix = {                                              #
#       # optionally limit the fix to a condtion                       #
#       _cond = {prov, ver, ... }: some boolean expression;            #
#                                                                      #
#       # define overrides                                             #
#       key-to-override = ...;                # to replace value       #
#       key-to-override.add = ...;            # to append value        #
#       key-to-override.mod = old_val: ...;   # to modify value        #
#     };                                                               #
#   };                                                                 #
#                                                                      #
########################################################################

### _cond ####################################
#  possible arguments:                       #
#   - prov  (provider of the package)        #
#   - ver   (version of the package)         #
#   - pyver (python version used)            #
##############################################

  ldap0 = {
    add-inputs = {
      buildInputs.add = with pkgs; [ openldap.dev cyrus_sasl.dev ];
    };
  };

  orange3 = {
    skipFixup = {
      dontFixup = true;
    };
  };

  tensorflow = {
    rm-tensorboard = {
      _cond = {prov, ... }: prov != "nixpkgs";
      postInstall = "rm $out/bin/tensorboard";
    };
  };

  tensorflow-gpu = tensorflow;

}
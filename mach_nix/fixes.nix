{ pkgs }:
with builtins;
with pkgs.lib;

# some basic helper functions
let

  # evaluate arbitrary python expression and return json parsed result
  py_eval = str: fromJSON ( readFile (
    pkgs.runCommand "py-eval-result" { buildInputs = with pkgs; [ python3 python3Packages.packaging ]; } ''
      ${pkgs.python3}/bin/python -c "${str}" > $out
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

  # prevent the normal fitler from being used
  filter = raise "Error: only use filterSafe (doesn't crash on null input)";

  # filter function that doesn't crash on 'objects = null'
  # This is important because null will be returned whenever the attribute to modify doesn't exist
  filterSafe = func: objects: if isNull objects then [] else builtins.filter func objects;

in


### Put Fixes here
rec {

###  FORMAT  ##################################################################################
#                                                                                             #
#   package-to-fix = {                                                                        #
#     name-of-the-fix = {                                                                     #
#       # optionally limit the fix to a condtion                                              #
#       _cond = {prov, ver, ... }: some boolean expression;                                   #
#                                                                                             #
#       # define overrides                                                                    #
#       key-to-override = ...;                                 # replace                      #
#       key-to-override.add = ...;                             # append (list/attrs/string)   #
#       key-to-override.mod = oldVal: ...;                     # modify                       #
#       key-to-override.mod = pySelf: oldAttrs: oldVal: ...;   # modify (accessing all pkgs)  #
#     };                                                                                      #
#   };                                                                                        #
#                                                                                             #
###############################################################################################

### _cond ####################################
#  possible arguments:                       #
#   - prov  (provider of the package)        #
#   - ver   (version of the package)         #
#   - pyver (python version used)            #
##############################################

  cartopy.add-native-inputs = {
    _cond = { prov, ver, ... }: prov == "nixpkgs";
    nativeBuildInputs.add = with pkgs; [ geos ];
  };

  cryptography.no-rust-build = {
    _cond = { prov, ver, ... }: prov == "sdist" && comp_ver ver "<" "3.4";
    nativeBuildInputs.mod = old: filterSafe (inp: (inp.name or "") != "cargo-setup-hook.sh") old;
  };

  # remove if merged: https://github.com/NixOS/nixpkgs/pull/114384
  google-auth.six-input-missing = {
    propagatedBuildInputs.mod = pySelf: _: oldVal: oldVal ++ [ pySelf.six ];
  };

  httpx.remove-patches = {
    _cond = { prov, ver, ... }:
      prov != "nixpkgs" &&
      comp_ver ver "!=" pkgs.python3Packages.httpx.version;
    patches = [];
  };

  ldap0.add-inputs = {
    buildInputs.add = with pkgs; [ openldap.dev cyrus_sasl.dev ];
  };

  # libwebp-base depends on libwebp containing redundant binaries
  libwebp-base.remove-colliding-bin = {
    _cond = { prov, ... }: prov == "conda";
    postInstall.add = ''
      rm -f $out/bin/{webpinfo,webpmux}
      rm -rf $out/lib
    '';
  };

  mariadb.add-mariadb-connector-c = {
    _cond = { prov, ... }: prov != "nixpkgs";
    MARIADB_CONFIG = "${pkgs.mariadb-connector-c}/bin/mariadb_config";
  };

  pip.remove-reproducible-patch = {
    _cond = { prov, ver, ... }: prov == "sdist" && comp_ver ver "<" "20.0";
    patches.mod = oldPatches: filterSafe (patch: ! hasSuffix "reproducible.patch" patch) oldPatches;
  };

  pyjq.add-native-inputs = {
    _cond = { prov, ver, ... }: prov == "sdist";
    nativeBuildInputs.add = with pkgs; [ autoconf automake libtool ];
  };

  rpy2.remove-pandas-patch = {
    _cond = { prov, ver, ... }:
      # https://github.com/rpy2/rpy2/commit/fbd060e364b70012e8d26cc74df04ee53f769379
      # https://github.com/rpy2/rpy2/commit/39e1cb6fca0d4107f1078727d8670c422e3c6f7f
      prov == "sdist"
      && comp_ver ver ">=" "3.2.6";
    patches.mod = oldPatches: filterSafe (p: ! hasSuffix "pandas-1.x.patch" p) oldPatches;
  };

  tensorflow.rm-tensorboard = {
    _cond = {prov, ... }: ! elem prov [ "nixpkgs" "conda" ];
    postInstall = "rm $out/bin/tensorboard";
  };

  tensorflow-gpu = tensorflow;

  websockets.remove-patchPhase = {
    _cond = {prov, ... }: elem prov [ "sdist" "nixpkgs" ];
    patchPhase = "";
  };

  deepspeed-mii.remove-asyncio = {
    _cond = ({ pyver, ... }:
      # asyncio becomes a built-in library since Python 3.4
      comp_ver pyver ">=" "3.4");
    propagatedBuildInputs.mod =
      filterSafe (input: input.pname != "asyncio");
  };
  
  gradio.linkify-it-py-missing = {
    propagatedBuildInputs.mod = pySelf: _: oldVal: oldVal ++ [ pySelf.linkify-it-py ];
  };
}

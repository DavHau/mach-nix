pkgs: python: with pkgs.lib;
  let 
    namePrefix = python.libPrefix + "-";
    makeOverridablePythonPackage = f: origArgs:
      let
        ff = f origArgs;
        overrideWith = newArgs: origArgs // (if isFunction newArgs then newArgs origArgs else newArgs);
      in
        if builtins.isAttrs ff then (ff // {
          overridePythonAttrs = newArgs: makeOverridablePythonPackage f (overrideWith newArgs);
        })
        else if builtins.isFunction ff then {
          overridePythonAttrs = newArgs: makeOverridablePythonPackage f (overrideWith newArgs);
          __functor = self: ff;
        }
        else ff;
    toPythonModule = drv:
      drv.overrideAttrs( oldAttrs: {
        # Use passthru in order to prevent rebuilds when possible.
        passthru = (oldAttrs.passthru or {})// {
          pythonModule = python;
          pythonPath = [ ]; # Deprecated, for compatibility.
          requiredPythonModules = python.pkgs.requiredPythonModules drv.propagatedBuildInputs;
        };
      });
    callPackage = pkgs.newScope python.pkgs;
  in
  pySelf: pySuper: {
    buildPythonPackage = makeOverridablePythonPackage (
      makeOverridable (callPackage "${pkgs.path}/pkgs/development/interpreters/python/mk-python-derivation.nix" {
        inherit namePrefix;     # We want Python libraries to be named like e.g. "python3.6-${name}"
        inherit toPythonModule; # Libraries provide modules

        # this prevents infinite recursions when overriding setuptools later
        setuptools = python.pkgs.setuptools;
      })
    );

    buildPythonApplication = makeOverridablePythonPackage (
      makeOverridable (callPackage "${pkgs.path}/pkgs/development/interpreters/python/mk-python-derivation.nix" {
        namePrefix = "";        # Python applications should not have any prefix
        toPythonModule = x: x;  # Application does not provide modules.

        # this prevents infinite recursions when overriding setuptools later
        setuptools = python.pkgs.setuptools;
      })
    );
  }

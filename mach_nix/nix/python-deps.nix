{python, fetchurl, ...}:
rec {
  distlib = python.pkgs.buildPythonPackage {
    name = "distlib-0.3.3";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/56/ed/9c876a62efda9901863e2cc8825a13a7fcbda75b4b498103a4286ab1653b/distlib-0.3.3.zip";
      sha256 = "01bbw4gm64fvdnlylqhsy3fhxs4yjhfnk3pcwassmspn3xsx10nr";
    };
    doCheck = false;
  };
  resolvelib = python.pkgs.buildPythonPackage {
    name = "resolvelib-0.4.0";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/20/64/5a93bc4f169f84c45107e69292a5a81d63fa50b6a23431005a68c6ae888c/resolvelib-0.4.0.tar.gz";
      sha256 = "93e42cf712534cf8dccb146c0c20521a5ac344ef8ec6e7742a49b22a24335662";
    };
    doCheck = false;
  };
  tree-format = python.pkgs.buildPythonPackage {
    name = "tree-format-0.1.2";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/0d/91/8d860c75c3e70e6bbec7b898b5f753bf5da404be9296e245034360759645/tree-format-0.1.2.tar.gz";
      sha256 = "a538523aa78ae7a4b10003b04f3e1b37708e0e089d99c9d3b9e1c71384c9a7f9";
    };
    doCheck = false;
  };

  networkx = python.pkgs.networkx;
  packaging = python.pkgs.packaging;
  setuptools = python.pkgs.setuptools;
  toml = python.pkgs.toml;
  wheel = python.pkgs.wheel;
}

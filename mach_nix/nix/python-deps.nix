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
    name = "resolvelib-0.3.0";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/e1/84/5c20d9bed18041343eeb537cc2b76aa17c18102ecf5873c12cd78a04cc69/resolvelib-0.3.0.tar.gz";
      sha256 = "9781c2038be2ba3377d075dd3aa8f5f0f7b508b6f59779b1414bea08ed402f1e";
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

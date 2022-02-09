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
    name = "resolvelib-0.6.0";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/ab/38/6564745f294e7182b1d2fcb04acde9c74f376f63e0fd0be6788af176fcc8/resolvelib-0.6.0.tar.gz";
      sha256 = "9da653f664be0fba1a1ee9b339f0046a84d084e5c1bcab0469eab941a63f5117";
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

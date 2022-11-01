{python, fetchurl, ...}:
rec {
  distlib = python.pkgs.buildPythonPackage {
    name = "distlib-0.3.7.dev.0";
    src = fetchurl {
      # PR fixing python_full_version: https://github.com/pypa/distlib/pull/187
      url = "https://github.com/pypa/distlib/archive/61534987ec5e4b3bdd346de8ffcc7aeaeb132572.zip";
      sha256 = "0mrp73k6nh3cphbamsv9k330irz5xnzays6d66w6xf857xj1gfx1";
    };
    format = "pyproject";
    doCheck = false;
  };
  resolvelib = python.pkgs.buildPythonPackage {
    name = "resolvelib-0.8.1";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/ac/20/9541749d77aebf66dd92e2b803f38a50e3a5c76e7876f45eb2b37e758d82/resolvelib-0.8.1.tar.gz";
      sha256 = "c6ea56732e9fb6fca1b2acc2ccc68a0b6b8c566d8f3e78e0443310ede61dbd37";
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

{python, fetchurl, ...}:
rec {
  resolvelib = python.pkgs.buildPythonPackage {
    name = "resolvelib-0.3.0";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/e1/84/5c20d9bed18041343eeb537cc2b76aa17c18102ecf5873c12cd78a04cc69/resolvelib-0.3.0.tar.gz";
      sha256 = "9781c2038be2ba3377d075dd3aa8f5f0f7b508b6f59779b1414bea08ed402f1e";
    };
    doCheck = false;
  };
  distlib = python.pkgs.buildPythonPackage {
    name = "distlib-0.3.0";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/7d/29/694a3a4d7c0e1aef76092e9167fbe372e0f7da055f5dcf4e1313ec21d96a/distlib-0.3.0.zip";
      sha256 = "2e166e231a26b36d6dfe35a48c4464346620f8645ed0ace01ee31822b288de21";
    };
    doCheck = false;
  };
  toml = python.pkgs.buildPythonPackage {
    name = "toml-0.10.1";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/da/24/84d5c108e818ca294efe7c1ce237b42118643ce58a14d2462b3b2e3800d5/toml-0.10.1.tar.gz";
      sha256 = "926b612be1e5ce0634a2ca03470f95169cf16f939018233a670519cb4ac58b0f";
    };
    doCheck = false;
  };
  packaging = python.pkgs.packaging;
  setuptools = python.pkgs.setuptools;
}

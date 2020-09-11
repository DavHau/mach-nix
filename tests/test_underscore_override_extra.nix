let
  mach-nix = import ../.;
in
mach-nix.mkPython {
  extra_pkgs = [
    (mach-nix.buildPythonPackage {
      src = "https://www.web2ldap.de/download/web2ldap-1.5.96.tar.gz";
      _.ldap0.buildInputs.add = with mach-nix.nixpkgs; [ openldap.dev cyrus_sasl.dev ];
      _.ldap0.src = builtins.fetchGit {
        url = "https://gitlab.com/ae-dir/python-ldap0";
        ref = "refs/tags/v1.1.0";
      };
    })
  ];
}

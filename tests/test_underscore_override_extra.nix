let
  mach-nix = import ../.;
in
mach-nix.mkPython {
  extra_pkgs = [
    (mach-nix.buildPythonPackage {
      src = "https://gitlab.com/ae-dir/web2ldap/-/archive/v1.5.97/web2ldap-v1.5.97.tar.gz";
      _.ldap0.buildInputs = with mach-nix.nixpkgs; [ openldap.dev cyrus_sasl.dev ];
      _.ldap0.src = builtins.fetchGit {
        url = "https://gitlab.com/ae-dir/python-ldap0";
        ref = "refs/tags/v1.1.0";
      };
    })
  ];
}
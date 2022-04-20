{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
mach-nix.mkPython (baseArgsMkPython // {
  packagesExtra = [
    (mach-nix.buildPythonPackage {
      src = builtins.fetchGit {
        url = "https://code.stroeder.com/ldap/web2ldap";
        ref = "refs/tags/v1.5.97";
      };
      _.ldap0.buildInputs = with mach-nix.nixpkgs; [ openldap.dev cyrus_sasl.dev ];
      _.ldap0.src = builtins.fetchGit {
        url = "https://gitlab.com/ae-dir/python-ldap0";
        ref = "refs/tags/v1.1.0";
      };
    })
  ];
})

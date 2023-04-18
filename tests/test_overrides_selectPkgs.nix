{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  py = mach-nix.nixpkgs.python39;

  overr = mach-nix.mkPythonOverrides {
    requirements = ''
      requests
    '';
    _.requests.name = "foo";
  };

  py_final = py.override (oa: {
    packageOverrides = overr;
  });

  selected = py_final.pkgs.selectPkgs py_final.pkgs;
in
if selected == []
  || (elemAt selected 0).pname != "requests"
  || (elemAt selected 0).name != "foo"
then throw "Error"
else mach-nix.nixpkgs.hello

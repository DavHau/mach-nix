{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  pyEnv = mach-nix.mkPython {
    requirements = ''
      requests
    '';
    extra_pkgs = with mach-nix.rPackages; [
      data_table
    ];
  };
in

if pyEnv ? python.pkgs.requests
    && pyEnv ? python.pkgs.rpy2
    && elem mach-nix.rPackages.data_table pyEnv.python.pkgs.rpy2.buildInputs then
  { inherit pyEnv; }
else
  throw "Error"

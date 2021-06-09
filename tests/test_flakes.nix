{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  pyEnv = (builtins.getFlake (toString ../.)).packages.x86_64-linux.gen.python.requests;
  pyEnvDockerImage = (builtins.getFlake (toString ../.)).packages.x86_64-linux.gen.docker.requests;
in
(map (p:
  if p ? _passthru.python.pkgs.requests then
    p
  else
    throw "Error"
) [pyEnv pyEnvDockerImage])
++ [
  (if ! pyEnv ? _passthru.python.pkgs.requests then
    throw "Error with shell"
  else
    mach-nix.nixpkgs.hello)
]

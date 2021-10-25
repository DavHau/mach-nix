{
  baseArgsMkPython ? {},
  baseArgsBuildPythonPackage ? {},
  mach-nix ? import ../. {},
  system ? builtins.currentSystem or "x86_64-linux",
  ...
}:
with builtins;
let
  pyEnv = (builtins.getFlake (toString ../.)).packages.${system}.gen.python.requests;
  pyEnvDockerImage = (builtins.getFlake (toString ../.)).packages.${system}.gen.docker.requests;
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

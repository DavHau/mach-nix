{
  mach-nix ? import ../. {},
  ...
}:
with builtins;
let
  pyEnv = (builtins.getFlake (toString ../.)).packages.x86_64-linux.pythonWith.requests;
  pyEnvShell = (builtins.getFlake (toString ../.)).packages.x86_64-linux.shellWith.requests;
  pyEnvDockerImage = (builtins.getFlake (toString ../.)).packages.x86_64-linux.dockerImageWith.requests;
in
(map (p:
  if p ? _passthru.python.pkgs.requests then
    p
  else
    throw "Error"
) [pyEnv pyEnvDockerImage])
++ [
  (if ! pyEnvShell ? _passthru.python.pkgs.requests then
    throw "Error with shell"
  else
    mach-nix.nixpkgs.hello)
]

with builtins;

let
  lock = (fromJSON (readFile ../../flake.lock)).nodes;
  get = input: {
    rev = lock."${input}".locked.rev;
    sha256 = lock."${input}".locked.narHash;
  };
in
 get

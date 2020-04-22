input:
let
  expression = import ./expression.nix input;
in
  import "${expression}/share/expr.nix"

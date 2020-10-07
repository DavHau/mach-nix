{ mkPython, pkgs, pypiFetcher, ... }:
with builtins;
let
  names = pypiFetcher.allNames;
  gen = shell: selected:
    let
      machnix = mkPython {
        inherit pkgs;
        python = "python38";
        requirements = foldl' (a: b: a + "\n" + b) "" selected;
      };
      attrs_list = map (n:
          { name = n; value = (gen shell (selected ++ [n])); }
      ) names;
      drv = if shell then machnix.env else machnix;
      pyEnv = drv.overrideAttrs (oa: {
        passthru =
          listToAttrs attrs_list
          // { _passthru = machnix.passthr; };
      });
    in
      pyEnv;

in
{
 "with" = gen false [];
 "shellWith" = gen true [];
}

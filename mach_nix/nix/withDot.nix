{ mkPython, pypiFetcher, ... }:
with builtins;
let
  names = pypiFetcher.allNames;
  gen = attr: selected:
    let
      pyEnvBase = mkPython {
        python = "python38";
        requirements = foldl' (a: b: a + "\n" + b) "" selected;
      };
      attrs_list = map (n:
          { name = n; value = (gen attr (selected ++ [n])); }
      ) names;
      drv = if attr == "" then pyEnvBase else pyEnvBase."${attr}";
      pyEnv = drv.overrideAttrs (oa: {
        passthru =
          listToAttrs attrs_list
          // { _passthru = pyEnv.passthr; };
      });
    in
      pyEnv;

in
{
 "with" = gen "" [];
 "shellWith" = gen "env" [];
 "dockerImageWith" = gen "dockerImage" [];
}

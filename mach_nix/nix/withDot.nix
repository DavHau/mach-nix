{ mkPython, pypiFetcher, ... }:
with builtins;
let
  names = pypiFetcher.allNames;
  gen = attr: selected:
    let
      pyEnvBase = mkPython {
        requirements = foldl' (a: b: a + "\n" + b) "" selected;
        ignoreCollisions = true;
      };
      attrs_list = map (n:
          { name = n; value = (gen attr (selected ++ [n])); }
      ) (filter (n: n!= "meta") names);
      drv = if attr == "" then pyEnvBase else pyEnvBase."${attr}";
      pyEnv = drv.overrideAttrs (oa: {
        passthru =
          listToAttrs attrs_list
          // { _passthru = pyEnvBase.passthru; };
      });
    in
      pyEnv;

in
{
 "pythonWith" = gen "" [];
 "dockerImageWith" = gen "dockerImage" [];
}

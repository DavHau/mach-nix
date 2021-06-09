{
  pkgs ? import (import ./mach_nix/nix/nixpkgs-src.nix) { config = {}; },
  pypiData ? (import ./mach_nix/nix/deps-db-and-fetcher.nix {
    inherit pkgs;
  }).pypi_deps_db_src,
  chondaChannelsJson ? import ./mach_nix/nix/conda-channels.nix {
    providers = { _default = [ "conda/main" "conda/r" "conda/conda-forge"]; };
  },
  ...
}:
let
  pythonWithPkgs = import ./mach_nix/nix/python.nix {
    inherit pkgs;
    dev = true;
  };
in
pkgs.mkShell {
  buildInputs =
    [ pythonWithPkgs ]
    ++
    (with pkgs; [
      nix-prefetch-git
      parallel
    ]);
  shellHook = ''
    export PYTHONPATH=$(pwd)/
    export PYPI_DATA=${pypiData}
    export CONDA_DATA=${chondaChannelsJson.condaChannelsJson}
    git config core.hooksPath ./git-hooks
  '';
}

{pypiData, argsJSON}: (import ./default.nix { inherit pypiData; } ).extractor-fast (builtins.fromJSON argsJSON)

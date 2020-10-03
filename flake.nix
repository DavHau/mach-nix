{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShell = import ./shell.nix {
          inherit pkgs;
        };
        packages =
          { mach-nix = import ./default.nix {inherit pkgs;}; };
          # generate python packages for all known pypi sources here
          # // builtins.foldl' (a: b: a // b) {} ;

        defaultPackage = self.packages."${system}".mach-nix.mach-nix;

        apps.mach-nix = flake-utils.lib.mkApp { drv = self.packages.mach-nix.mach-nix; };
        defaultApp = { type = "app"; program = "${self.defaultPackage."${system}"}/bin/mach-nix"; };
      }
  );
}


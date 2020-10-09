{

  description = "Create highly reproducible python environments";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        mach-nix-default = import ./default.nix {inherit pkgs;};
      in
      {
        devShell = import ./shell.nix {
          inherit pkgs;
        };
        packages = rec {
          mach-nix = mach-nix-default.mach-nix;
          "with" = mach-nix-default."with";
          shellWith = mach-nix-default.shellWith;
        };

        defaultPackage = self.packages."${system}".mach-nix.mach-nix;

        apps.mach-nix = flake-utils.lib.mkApp { drv = self.packages.mach-nix.mach-nix; };
        defaultApp = { type = "app"; program = "${self.defaultPackage."${system}"}/bin/mach-nix"; };
      }
  );
}

